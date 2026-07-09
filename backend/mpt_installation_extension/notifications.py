import datetime as dt
from typing import Any

import httpx
from mpt_extension_contrib.custom_notifications.channels.teams_async import AsyncTeamsNotifier
from mpt_extension_contrib.custom_notifications.channels.teams_cards import FactsSection

from mpt_installation_extension.pipelines.context import InstallationAgreementContext


async def notify_non_recoverable_failure(ctx: InstallationAgreementContext) -> None:
    """Send a Teams notification for a non-recoverable installation failure."""
    action = ctx.installation_state.action
    if action is None:
        return

    try:
        teams = ctx.notifications.get(AsyncTeamsNotifier)
    except (LookupError, ValueError) as error:
        ctx.logger.warning(
            "Teams notifications are not available; skipping non-recoverable "
            "installation failure notification for agreement %s: %s",
            ctx.agreement.id,
            error,
        )
        return

    try:
        await teams.send_error(
            "Extension installation failed permanently",
            action.message,
            facts=_build_facts(action.details),
        )
    # HACK: catching the transport exception is a workaround that couples us to the
    # library's httpx internals; replace it with the library's own delivery error
    # once mpt-extension-contrib-custom-notifications exposes one.
    except httpx.HTTPError as error:
        ctx.logger.warning(
            "Failed to deliver the Teams notification for agreement %s: %s",
            ctx.agreement.id,
            error,
        )


def _build_facts(details: dict[str, Any]) -> FactsSection:
    entries = {
        "Extension": str(details["extension_id"]),
        "Agreement": str(details["agreement_id"]),
        "Product": str(details["product_id"]),
        "Client": str(details["client_id"]),
        "Timestamp": dt.datetime.now(dt.UTC).isoformat(),
    }
    for failure in details.get("failures", ()):
        failure_summary = f"{failure['error_type']}: {failure['message']}"
        entries[str(failure["extension_id"])] = failure_summary
    return FactsSection(title="Failure details", entries=entries)
