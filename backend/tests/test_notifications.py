import dataclasses
import datetime as dt

import httpx
import pytest
from mpt_extension_contrib.custom_notifications import NotificationRegistry
from mpt_extension_contrib.custom_notifications.channels.teams import TeamsNotifications

from mpt_installation_extension.notifications import notify_non_recoverable_failure
from mpt_installation_extension.pipelines.context import (
    InstallationAction,
    InstallationActionType,
)


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
def teams_mock(mocker):
    return mocker.Mock(spec_set=TeamsNotifications)


@pytest.fixture
def teams_registry(teams_mock):
    registry = NotificationRegistry()
    registry.register("teams", teams_mock, override=True)
    return registry


@pytest.fixture
def notifying_context(failure_context, teams_registry):
    failure_context.notifications = teams_registry
    return failure_context


def test_sends_error_card_message(notifying_context, teams_mock, mocker):
    notify_non_recoverable_failure(notifying_context)  # act

    teams_mock.send_error.assert_has_calls([
        mocker.call(
            "Extension installation failed permanently",
            "One or more extension installations failed permanently",
            facts=mocker.ANY,
        ),
    ])


def test_sends_error_card_facts(notifying_context, teams_mock):
    notify_non_recoverable_failure(notifying_context)  # act

    facts = teams_mock.send_error.call_args.kwargs["facts"]
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


def test_warns_when_delivery_fails(notifying_context, teams_mock):
    teams_mock.send_error.side_effect = httpx.ConnectTimeout("timed out")

    notify_non_recoverable_failure(notifying_context)  # act

    notifying_context.logger.warning.assert_called_once()


def test_warns_when_teams_not_configured(failure_context):
    notify_non_recoverable_failure(failure_context)  # act

    failure_context.logger.warning.assert_called_once()


def test_warns_when_webhook_is_not_https(failure_context):
    failure_context.ext_settings = dataclasses.replace(
        failure_context.ext_settings,
        teams_webhook_url="<fake-msteams-webhook-url>",
    )

    notify_non_recoverable_failure(failure_context)  # act

    failure_context.logger.warning.assert_called_once()


def test_noop_without_action(agreement_context_factory, teams_mock, teams_registry):
    ctx = agreement_context_factory(context_type="installation")
    ctx.notifications = teams_registry

    notify_non_recoverable_failure(ctx)  # act

    teams_mock.send_error.assert_not_called()
