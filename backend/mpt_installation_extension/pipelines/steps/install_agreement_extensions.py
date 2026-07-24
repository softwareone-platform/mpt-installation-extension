import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar, cast, override

from mpt_api_client.exceptions import MPTError
from mpt_extension_sdk.errors.step import DeferStepError, SkipStepError
from mpt_extension_sdk.pipeline import BaseStep

from mpt_installation_extension.pipelines.context import (
    InstallationAction,
    InstallationActionType,
    InstallationAgreementContext,
)
from mpt_installation_extension.pipelines.errors import (
    RecoverableInstallationError,
    is_deferrable_error,
)
from mpt_installation_extension.services.extension_installation import (
    ExtensionInstallationCreatorService,
)

_OutcomeT = TypeVar("_OutcomeT")


class ProductExtensionMappingSettings(Protocol):
    """Settings required by the agreement extension installation step."""

    product_extension_mapping: dict[str, Sequence[str]]


@dataclass(frozen=True)
class InstallationFailure:
    """Non-recoverable installation failure details."""

    extension_id: str
    error_type: str
    message: str
    status_code: int | None = None

    @classmethod
    def from_error(cls, extension_id: str, error: MPTError) -> "InstallationFailure":
        """Build failure details from an MPT API error."""
        return cls(
            extension_id=extension_id,
            error_type=error.__class__.__name__,
            message=str(error),
            status_code=getattr(error, "status_code", None),
        )

    def to_dict(self) -> dict[str, str | int | None]:
        """Return serializable failure details."""
        return {
            "extension_id": self.extension_id,
            "error_type": self.error_type,
            "message": self.message,
            "status_code": self.status_code,
        }


class InstallAgreementExtensionsStep(BaseStep):
    """Install configured vendor extensions for an active agreement."""

    @override
    async def pre(self, ctx: InstallationAgreementContext) -> None:
        product_id = ctx.agreement.product.id
        if not self._get_extension_ids(ctx, product_id):
            raise SkipStepError(
                f"No extension installations configured for product {product_id}",
            )

    @override
    async def process(self, ctx: InstallationAgreementContext) -> None:
        step_outcomes = await asyncio.gather(
            *(
                self._install_extension(ctx, extension_id)
                for extension_id in self._get_extension_ids(ctx, ctx.agreement.product.id)
            ),
            return_exceptions=True,
        )

        failures = self._get_outcomes_by_type(step_outcomes, InstallationFailure)
        if failures:
            ctx.installation_state.action = InstallationAction(
                target=InstallationActionType.NOTIFY_NON_RECOVERABLE_FAILURE,
                message="One or more extension installations failed permanently",
                details={
                    "extension_id": ctx.runtime_settings.extension_id,
                    "agreement_id": ctx.agreement.id,
                    "product_id": ctx.agreement.product.id,
                    "client_id": ctx.agreement.client.id,
                    "failures": [failure.to_dict() for failure in failures],
                },
            )

        recoverable_errors = self._get_outcomes_by_type(step_outcomes, RecoverableInstallationError)
        if recoverable_errors:
            extension_ids = ", ".join(error.extension_id for error in recoverable_errors)
            raise DeferStepError(
                f"Recoverable extension installation failure for extensions {extension_ids}",
            )

        unexpected_errors = [
            error
            for error in self._get_outcomes_by_type(step_outcomes, Exception)
            if not isinstance(error, RecoverableInstallationError)
        ]
        if unexpected_errors:
            raise unexpected_errors[0]

    def _get_extension_ids(
        self, ctx: InstallationAgreementContext, product_id: str
    ) -> tuple[str, ...]:
        ext_settings = cast(ProductExtensionMappingSettings, ctx.ext_settings)
        return tuple(ext_settings.product_extension_mapping.get(product_id, ()))

    def _get_outcomes_by_type(
        self, step_outcomes: Sequence[object], outcome_type: type[_OutcomeT]
    ) -> list[_OutcomeT]:
        return [
            step_outcome for step_outcome in step_outcomes if isinstance(step_outcome, outcome_type)
        ]

    def _handle_mpt_error(self, extension_id: str, error: MPTError) -> InstallationFailure:
        if is_deferrable_error(error):
            raise RecoverableInstallationError(extension_id, error)
        return InstallationFailure.from_error(extension_id, error)

    async def _install_extension(
        self, ctx: InstallationAgreementContext, extension_id: str
    ) -> InstallationFailure | None:
        service = ExtensionInstallationCreatorService(ctx.mpt_api_service)
        try:
            await service.create_installation(
                account_id=ctx.agreement.client.id, extension_id=extension_id
            )
        except MPTError as error:
            return self._handle_mpt_error(extension_id, error)
        return None
