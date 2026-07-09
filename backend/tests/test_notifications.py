import dataclasses
import datetime as dt

import httpx
import pytest
from mpt_extension_contrib.custom_notifications import NotificationRegistry
from mpt_extension_contrib.custom_notifications.channels.teams_async import AsyncTeamsNotifier

from mpt_installation_extension.notifications import notify_non_recoverable_failure
from mpt_installation_extension.pipelines.context import (
    InstallationAction,
    InstallationActionType,
)


class StubTeamsNotifier(AsyncTeamsNotifier):
    """Registry lookup is nominal, so the test double must subclass the notifier."""

    def __init__(self, send_error_mock):
        self.send_error = send_error_mock


@pytest.fixture
def failure_context(agreement_context_factory):
    ctx = agreement_context_factory(context_type="installation")
    ctx.installation_state.action = InstallationAction(
        target=InstallationActionType.NOTIFY_NON_RECOVERABLE_FAILURE,
        message="One or more extension installations failed permanently",
        details={
            "extension_id": "EXT-1111-1111",
            "agreement_id": "AGR-1",
            "product_id": "PRD-1111",
            "client_id": "ACC-CLIENT",
            "failures": [
                {
                    "extension_id": "EXT-1111",
                    "error_type": "MPTAPIError",
                    "message": "404 Not found - Not found (no-trace-id)",
                    "status_code": 404,
                },
                {
                    "extension_id": "EXT-2222",
                    "error_type": "MPTError",
                    "message": "invalid extension configuration",
                    "status_code": None,
                },
            ],
        },
    )
    return ctx


@pytest.fixture
def send_error_mock(mocker):
    return mocker.AsyncMock()


@pytest.fixture
def teams_registry(send_error_mock):
    registry = NotificationRegistry()
    registry.register("teams_async", StubTeamsNotifier(send_error_mock), override=True)
    return registry


@pytest.fixture
def notifying_context(failure_context, teams_registry):
    failure_context.notifications = teams_registry
    return failure_context


async def test_sends_error_card_message(notifying_context, send_error_mock, mocker):
    await notify_non_recoverable_failure(notifying_context)  # act

    send_error_mock.assert_awaited_once_with(
        "Extension installation failed permanently",
        "One or more extension installations failed permanently",
        facts=mocker.ANY,
    )


async def test_sends_error_card_facts(notifying_context, send_error_mock):
    await notify_non_recoverable_failure(notifying_context)  # act

    facts = send_error_mock.await_args.kwargs["facts"]
    timestamp = facts.entries.pop("Timestamp")
    assert facts.title == "Failure details"
    assert facts.entries == {
        "Extension": "EXT-1111-1111",
        "Agreement": "AGR-1",
        "Product": "PRD-1111",
        "Client": "ACC-CLIENT",
        "EXT-1111": "MPTAPIError: 404 Not found - Not found (no-trace-id)",
        "EXT-2222": "MPTError: invalid extension configuration",
    }
    assert dt.datetime.fromisoformat(timestamp).tzinfo is not None


async def test_warns_when_delivery_fails(notifying_context, send_error_mock):
    send_error_mock.side_effect = httpx.ConnectTimeout("timed out")

    await notify_non_recoverable_failure(notifying_context)  # act

    notifying_context.logger.warning.assert_called_once()


async def test_warns_when_teams_not_configured(failure_context):
    await notify_non_recoverable_failure(failure_context)  # act

    failure_context.logger.warning.assert_called_once()


async def test_warns_when_enabled_without_webhook(failure_context):
    failure_context.ext_settings = dataclasses.replace(
        failure_context.ext_settings,
        teams_notifications_enabled=True,
    )

    await notify_non_recoverable_failure(failure_context)  # act

    failure_context.logger.warning.assert_called_once()


async def test_warns_when_webhook_is_not_https(failure_context):
    failure_context.ext_settings = dataclasses.replace(
        failure_context.ext_settings,
        teams_webhook_url="<fake-msteams-webhook-url>",
        teams_notifications_enabled=True,
    )

    await notify_non_recoverable_failure(failure_context)  # act

    failure_context.logger.warning.assert_called_once()


async def test_noop_without_action(agreement_context_factory, send_error_mock, teams_registry):
    ctx = agreement_context_factory(context_type="installation")
    ctx.notifications = teams_registry

    await notify_non_recoverable_failure(ctx)  # act

    send_error_mock.assert_not_awaited()
