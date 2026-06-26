from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.api.models.events import Event

from mpt_installation_extension.pipelines.agreement_installation import (
    AgreementInstallationPipeline,
)
from mpt_installation_extension.pipelines.context import InstallationAgreementContext
from mpt_installation_extension.settings import get_extension_settings

router = EventRouter(prefix="/events/v2/agreements")
settings = get_extension_settings()


@router.event(
    path="/complete",
    name="agreements-complete",
    event="platform.commerce.agreement.status_changed",
    condition=f"and(in(product.id,{settings.product_ids_rql}),eq(status,Active))",
    context_adapter_type=InstallationAgreementContext,
)
async def handle_agreement_completed(event: Event, ctx: InstallationAgreementContext) -> None:
    """Create configured vendor extension installations after agreement activation."""
    await AgreementInstallationPipeline().execute(ctx)
