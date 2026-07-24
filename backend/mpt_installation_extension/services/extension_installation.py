import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from http import HTTPStatus
from itertools import starmap
from typing import Self, cast

from mpt_api_client.exceptions import MPTHttpError
from mpt_extension_sdk.models import Installation, InstallationReference
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

from mpt_installation_extension.services.agreement_query import AgreementQueryService

logger = logging.getLogger(__name__)


class InstallOutcome(StrEnum):
    """Outcome of an installation attempt."""

    CREATED = "Created"
    ALREADY_EXISTS = "AlreadyExists"


@dataclass(frozen=True)
class FailedInstallation:
    """A single account/extension pair that failed to install."""

    account_id: str
    extension_id: str
    error: str


@dataclass
class InstallationReport:
    """Aggregated result of a bulk installation run."""

    created: int = 0
    already_exists: int = 0
    failures: list[FailedInstallation] = field(default_factory=list)

    def merge(self, other: Self) -> None:
        """Fold another report into this one."""
        self.created += other.created
        self.already_exists += other.already_exists
        self.failures.extend(other.failures)

    def record(
        self, *, account_id: str, extension_id: str, outcome: "InstallOutcome | BaseException"
    ) -> None:
        """Count a single installation outcome, capturing failures."""
        if isinstance(outcome, BaseException):
            self.failures.append(
                FailedInstallation(
                    account_id=account_id, extension_id=extension_id, error=str(outcome)
                )
            )
        elif outcome == InstallOutcome.CREATED:
            self.created += 1
        else:
            self.already_exists += 1


class ExtensionInstallationCreatorService:
    """Create vendor extension installations for Marketplace accounts.

    Installation is idempotent: a create returning ``409 CONFLICT`` is treated as
    an existing installation, so no separate existence check is needed.
    """

    def __init__(
        self, mpt_api_service: MPTAPIService, agreement_query: AgreementQueryService | None = None
    ) -> None:
        self._mpt = mpt_api_service
        self._agreements = agreement_query or AgreementQueryService(mpt_api_service)

    async def create_installation(self, *, account_id: str, extension_id: str) -> InstallOutcome:
        """Create the installation for the account, tolerating an existing one."""
        modules = await self._extension_modules(extension_id)
        return await self._create(account_id=account_id, extension_id=extension_id, modules=modules)

    async def create_missing_installations(
        self, targets: Mapping[str, Sequence[str]]
    ) -> InstallationReport:
        """Create the given extension installations on all accounts that lack them.

        Args:
            targets: Mapping of ``product_id -> [extension_id, ...]``. For each
                product, every account with an ``Active`` agreement of that product
                gets each extension installed if missing.

        Returns:
            An `InstallationReport` with created/already-existing counts and per-item
            failures. Failures do not abort the run; they are aggregated for the caller.
        """
        product_reports = await asyncio.gather(*starmap(self._install_product, targets.items()))
        report = InstallationReport()
        for product_report in product_reports:
            report.merge(product_report)
        return report

    async def _create(
        self, *, account_id: str, extension_id: str, modules: Sequence[str]
    ) -> InstallOutcome:
        installation = Installation(
            account=InstallationReference(id=account_id),
            extension=InstallationReference(id=extension_id),
            modules=[InstallationReference(id=module_id) for module_id in modules],
        )
        try:
            await self._mpt.installations.create(installation)
        except MPTHttpError as error:
            if error.status_code != HTTPStatus.CONFLICT:
                raise
            logger.info(
                "Skipping installation for account %s, extension %s: already exists",
                account_id,
                extension_id,
            )
            return InstallOutcome.ALREADY_EXISTS

        logger.info(
            "Created installation for account %s, extension %s",
            account_id,
            extension_id,
        )
        return InstallOutcome.CREATED

    async def _extension_modules(self, extension_id: str) -> list[str]:
        extension = await self._mpt.extensions.get_by_id(extension_id)
        return [cast(str, module.id) for module in extension.modules]

    async def _install_extension(
        self, extension_id: str, account_ids: Sequence[str]
    ) -> InstallationReport:
        modules = await self._extension_modules(extension_id)
        outcomes = await asyncio.gather(
            *(
                self._create(account_id=account_id, extension_id=extension_id, modules=modules)
                for account_id in account_ids
            ),
            return_exceptions=True,
        )
        report = InstallationReport()
        for account_id, outcome in zip(account_ids, outcomes, strict=True):
            report.record(account_id=account_id, extension_id=extension_id, outcome=outcome)
        return report

    async def _install_product(
        self, product_id: str, extension_ids: Sequence[str]
    ) -> InstallationReport:
        account_ids = await self._agreements.active_account_ids(product_id)
        logger.info(
            "Creating missing installations for product %s: %s accounts, extensions %s",
            product_id,
            len(account_ids),
            list(extension_ids),
        )
        extension_reports = await asyncio.gather(
            *(self._install_extension(extension_id, account_ids) for extension_id in extension_ids)
        )
        report = InstallationReport()
        for extension_report in extension_reports:
            report.merge(extension_report)
        return report
