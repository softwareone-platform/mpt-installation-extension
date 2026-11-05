import pytest
from mpt_extension_sdk.api.models.events import TaskEvent
from mpt_extension_sdk.errors.pipeline import FailError
from mpt_extension_sdk.models.task import TaskLog, TaskLogSeverity
from mpt_extension_sdk.routing import EventDeliveryMode

from mpt_installation_extension.pipelines.context import InstallationOutcome
from mpt_installation_extension.routers.events import agreements


@pytest.fixture
def task_event():
    return TaskEvent.model_validate({
        "id": "EVT-1",
        "task": {"id": "TSK-1"},
        "object": {"id": "AGR-1", "name": "Agreement", "objectType": "Agreement"},
        "details": {
            "eventType": "platform.commerce.agreement.status_changed",
            "enqueueTime": "2026-03-06T12:00:00Z",
            "deliveryTime": "2026-03-06T12:01:00Z",
        },
    })


@pytest.fixture
def installation_context(agreement_context_factory):
    return agreement_context_factory(context_type="installation")


@pytest.fixture
def task_service(mocker):
    service = mocker.Mock(spec_set=["create_log"])
    service.create_log = mocker.AsyncMock()
    mocker.patch.object(agreements, "get_tasks_service", autospec=True, return_value=service)
    return service


@pytest.fixture
def execute_mock(mocker):
    return mocker.patch.object(agreements.AgreementInstallationPipeline, "execute", autospec=True)


def test_registers_task_route():
    route = agreements.router.routes[0]  # act

    assert route.delivery_mode == EventDeliveryMode.TASK
    assert route.path == "/events/v2/agreements/complete"
    assert route.event == "platform.commerce.agreement.status_changed"


@pytest.mark.parametrize(
    ("outcome", "severity"),
    [
        (InstallationOutcome.CREATED, TaskLogSeverity.INFO),
        (InstallationOutcome.ALREADY_EXISTS, TaskLogSeverity.INFO),
        (InstallationOutcome.RETRY, TaskLogSeverity.WARNING),
        (InstallationOutcome.FAILED, TaskLogSeverity.ERROR),
    ],
)
async def test_handler_logs_to_event_task(  # noqa: WPS211
    installation_context, execute_mock, task_event, task_service, outcome, severity
):
    installation_context.installation_state.record("EXT-1111", outcome, "installation message")

    await agreements.handle_agreement_completed(task_event, installation_context)  # act

    task_service.create_log.assert_awaited_once_with(
        "TSK-1", TaskLog(message="installation message", severity=severity)
    )


async def test_handler_logs_when_pipeline_fails(
    installation_context, execute_mock, task_event, task_service
):
    installation_context.installation_state.record("EXT-1111", InstallationOutcome.FAILED, "failed")
    execute_mock.side_effect = FailError("failed")

    with pytest.raises(FailError):
        await agreements.handle_agreement_completed(task_event, installation_context)

    task_service.create_log.assert_awaited_once_with(
        "TSK-1", TaskLog(message="failed", severity=TaskLogSeverity.ERROR)
    )
