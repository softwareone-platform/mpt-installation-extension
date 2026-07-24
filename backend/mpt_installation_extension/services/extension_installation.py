import asyncio
import logging
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from itertools import starmap
from typing import cast

from mpt_api_client.exceptions import MPTError, MPTHttpError
from mpt_extension_sdk.models import Installation, InstallationReference

from mpt_installation_extension.services.installation_report import (
    InstallationReport,
    InstallOutcome,
)
from mpt_installation_extension.services.mpt_api_service import MPTAPIService

logger = logging.getLogger(__name__)

# Upper bound on concurrent installation requests across a whole reconciliation run,
# so a large backfill does not exhaust connections or trigger Marketplace rate limits.
MAX_CONCURRENT_INSTALLATIONS = 20


class ExtensionInstallationCreatorService:
    """Create vendor extension installations for Marketplace accounts.

    Installation is idempotent: a create returning ``409 CONFLICT`` is treated as
    an existing installation, so no separate existence check is needed.
    """

    def __init__(self, mpt_api_service: MPTAPIService) -> None:
        self._mpt_api_service = mpt_api_service
        self._create_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INSTALLATIONS)

    async def create_installation(self, *, account_id: str, extension_id: str) -> InstallOutcome:
        """Create the installation for the account, tolerating an existing one."""
        extension = await self._mpt_api_service.extensions.get_by_id(extension_id)
        modules = [cast(str, module.id) for module in extension.modules]
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
            async with self._create_semaphore:
                await self._mpt_api_service.installations.create(installation)
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

    async def _install_extension(
        self, extension_id: str, account_ids: Sequence[str]
    ) -> InstallationReport:
        try:
            return await self._reconcile_extension(extension_id, account_ids)
        except MPTError as error:
            logger.warning("Failed to reconcile extension %s; skipping it", extension_id)
            return InstallationReport.from_extension_error(extension_id, error)

    async def _reconcile_extension(
        self, extension_id: str, account_ids: Sequence[str]
    ) -> InstallationReport:
        existing = await self._mpt_api_service.installations.accounts_with_extension(extension_id)
        targets = [account_id for account_id in account_ids if account_id not in existing]
        if not targets:
            return InstallationReport(already_exists=len(account_ids))

        extension = await self._mpt_api_service.extensions.get_by_id(extension_id)
        modules = [cast(str, module.id) for module in extension.modules]
        outcomes = await asyncio.gather(
            *(
                self._create(account_id=account_id, extension_id=extension_id, modules=modules)
                for account_id in targets
            ),
            return_exceptions=True,
        )
        return InstallationReport.from_outcomes(
            extension_id, targets, outcomes, already_installed=len(account_ids) - len(targets)
        )

    async def _install_product(
        self, product_id: str, extension_ids: Sequence[str]
    ) -> InstallationReport:
        try:
            account_ids = await self._mpt_api_service.agreements.active_account_ids(product_id)
        except MPTError as error:
            logger.warning(
                "Failed to resolve active accounts for product %s; skipping it", product_id
            )
            return InstallationReport.from_product_error(extension_ids, error)

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
