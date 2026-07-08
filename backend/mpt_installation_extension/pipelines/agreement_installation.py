import asyncio
from typing import cast, override

from mpt_extension_sdk.pipeline import BasePipeline, BaseStep, EventBaseContext

from mpt_installation_extension.notifications import notify_non_recoverable_failure
from mpt_installation_extension.pipelines.context import (
    InstallationActionType,
    InstallationAgreementContext,
)
from mpt_installation_extension.pipelines.steps.install_agreement_extensions import (
    InstallAgreementExtensionsStep,
)


class AgreementInstallationPipeline(BasePipeline):
    """Pipeline that installs configured vendor extensions for active agreements."""

    @override
    @property
    def steps(self) -> list[BaseStep]:
        return [InstallAgreementExtensionsStep()]

    @override
    async def on_step_succeeded(self, step: BaseStep, ctx: EventBaseContext) -> None:
        await super().on_step_succeeded(step, ctx)

        installation_ctx = cast(InstallationAgreementContext, ctx)
        action = installation_ctx.installation_state.action
        if action is None or installation_ctx.installation_state.handled:
            return

        if action.target == InstallationActionType.NOTIFY_NON_RECOVERABLE_FAILURE:
            installation_ctx.logger.error(
                "Non-recoverable extension installation failure notification. "
                "agreement_id=%s details=%s",
                installation_ctx.agreement.id,
                action.details,
            )
            await asyncio.to_thread(notify_non_recoverable_failure, installation_ctx)

        installation_ctx.installation_state.handled = True
