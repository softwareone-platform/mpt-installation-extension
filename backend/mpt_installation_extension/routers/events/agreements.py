from types import MappingProxyType

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.api.builders.dependencies import get_tasks_service
from mpt_extension_sdk.api.models.events import TaskEvent
from mpt_extension_sdk.models.task import TaskLogSeverity
from mpt_extension_sdk.tasks import TaskHandle

from mpt_installation_extension.pipelines.agreement_installation import (
    AgreementInstallationPipeline,
)
from mpt_installation_extension.pipelines.context import (
    InstallationAgreementContext,
    InstallationOutcome,
)
from mpt_installation_extension.settings import get_extension_settings

router = EventRouter(prefix="/events/v2/agreements")
settings = get_extension_settings()

_LOG_SEVERITIES = MappingProxyType({
    InstallationOutcome.CREATED: TaskLogSeverity.INFO,
    InstallationOutcome.ALREADY_EXISTS: TaskLogSeverity.INFO,
    InstallationOutcome.RETRY: TaskLogSeverity.WARNING,
    InstallationOutcome.FAILED: TaskLogSeverity.ERROR,
})


@router.task(
    path="/complete",
    name="agreements-complete",
    event="platform.commerce.agreement.status_changed",
    condition=f"and(in(product.id,{settings.product_ids_rql}),eq(status,Active))",
    context_adapter_type=InstallationAgreementContext,
)
async def handle_agreement_completed(event: TaskEvent, ctx: InstallationAgreementContext) -> None:
    """Create configured vendor extension installations after agreement activation.

    The run is recorded on the delivery's platform task, whatever the pipeline outcome.
    """
    task = TaskHandle(id=event.task.id, task_service=get_tasks_service(ctx.runtime_settings))
    try:
        await AgreementInstallationPipeline().execute(ctx)
    finally:
        for installation in ctx.installation_state.installations:
            await task.log(  # noqa: WPS476
                installation.message, severity=_LOG_SEVERITIES[installation.outcome]
            )
