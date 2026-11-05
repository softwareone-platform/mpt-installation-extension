from http import HTTPStatus

import pytest
from mpt_api_client.exceptions import MPTError, MPTHttpError, MPTMaxRetryError
from mpt_extension_sdk.errors.pipeline import DeferError, FailError
from mpt_extension_sdk.errors.step import DeferStepError
from mpt_extension_sdk.models import Installation

from mpt_installation_extension.pipelines.agreement_installation import (
    AgreementInstallationPipeline,
)
from mpt_installation_extension.pipelines.context import (
    InstallationActionType,
    InstallationOutcome,
    InstallationResult,
)
from mpt_installation_extension.services.installation_report import (
    InstallOutcome,
    InstallResult,
)


@pytest.fixture
def pipeline():
    return AgreementInstallationPipeline()


@pytest.fixture
def installation_context(agreement_context_factory):
    return agreement_context_factory(context_type="installation")


async def test_pipeline_creates_installations(installation_context, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    extension_response = mocker.Mock(
        spec_set=["modules"],
        modules=[
            mocker.Mock(spec_set=["id"], id="MOD-1"),
            mocker.Mock(spec_set=["id"], id="MOD-2"),
        ],
    )
    extension_service.get_by_id = mocker.AsyncMock(return_value=extension_response)
    installation_service.create = mocker.AsyncMock(
        return_value=mocker.Mock(spec_set=["id"], id="INS-1")
    )

    await pipeline.execute(installation_context)  # act

    sent = installation_service.create.await_args.args[0]
    assert installation_service.create.await_count == 2
    assert isinstance(sent, Installation)
    assert [module.id for module in sent.modules] == ["MOD-1", "MOD-2"]


async def test_pipeline_shares_one_creator_service(installation_context, mocker, pipeline):
    service_cls = mocker.patch(
        "mpt_installation_extension.pipelines.steps.install_agreement_extensions."
        "ExtensionInstallationCreatorService",
    )
    service_cls.return_value.create_installation = mocker.AsyncMock(
        return_value=InstallResult(InstallOutcome.CREATED, "INS-1")
    )

    await pipeline.execute(installation_context)  # act

    # Two extensions are configured, but a single service (and semaphore) is shared.
    assert service_cls.call_count == 1
    create_installation = service_cls.return_value.create_installation
    installed_extension_ids = sorted(
        call.kwargs["extension_id"] for call in create_installation.await_args_list
    )
    assert installed_extension_ids == ["EXT-1111", "EXT-2222"]


async def test_pipeline_tolerates_existing(installation_context, make_mpt_error, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    extension_service.get_by_id = mocker.AsyncMock(
        return_value=mocker.Mock(spec_set=["modules"], modules=[])
    )
    installation_service.create = mocker.AsyncMock(
        side_effect=make_mpt_error(HTTPStatus.CONFLICT, "Conflict")
    )

    await pipeline.execute(installation_context)  # act

    assert installation_context.installation_state.action is None
    assert installation_service.create.await_count == 2


async def test_pipeline_defers_after_http_error(installation_context, mocker, pipeline):
    extension_service = installation_context.mpt_api_service.extensions
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=MPTHttpError(
            HTTPStatus.SERVICE_UNAVAILABLE, "Service unavailable", "unavailable"
        ),
    )

    with pytest.raises(DeferError) as error:
        await pipeline.execute(installation_context)

    assert error.value.delay_seconds == DeferStepError().delay_seconds


async def test_pipeline_defers_after_max_retry_error(installation_context, mocker, pipeline):
    extension_service = installation_context.mpt_api_service.extensions
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=MPTMaxRetryError("Marketplace request", 3),
    )

    with pytest.raises(DeferError) as error:
        await pipeline.execute(installation_context)

    assert error.value.delay_seconds == DeferStepError().delay_seconds


async def test_pipeline_records_failure_action(
    installation_context, make_mpt_error, mocker, pipeline
):
    ctx = installation_context
    extension_service = installation_context.mpt_api_service.extensions
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=make_mpt_error(HTTPStatus.NOT_FOUND, "Not found"),
    )

    with pytest.raises(FailError):
        await pipeline.execute(ctx)

    assert ctx.installation_state.action.details["failures"] == [
        {
            "extension_id": "EXT-1111",
            "error_type": "MPTAPIError",
            "message": "404 Not found - Not found (no-trace-id)",
            "status_code": HTTPStatus.NOT_FOUND,
        },
        {
            "extension_id": "EXT-2222",
            "error_type": "MPTAPIError",
            "message": "404 Not found - Not found (no-trace-id)",
            "status_code": HTTPStatus.NOT_FOUND,
        },
    ]
    assert ctx.installation_state.action.details["extension_id"] == "EXT-1111-1111"
    assert ctx.installation_state.action.target == (
        InstallationActionType.NOTIFY_NON_RECOVERABLE_FAILURE
    )
    assert ctx.installation_state.handled is True


async def test_pipeline_records_action_and_defers(installation_context, mocker, pipeline):
    ctx = installation_context
    extension_service = installation_context.mpt_api_service.extensions
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=[
            MPTError("invalid extension configuration"),
            MPTHttpError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Service unavailable",
                "unavailable",
            ),
        ],
    )

    with pytest.raises(DeferError):
        await pipeline.execute(ctx)

    non_recoverable_call = extension_service.get_by_id.await_args_list[0]
    non_recoverable_extension_id = non_recoverable_call.args[0]
    assert ctx.installation_state.action.details["failures"] == [
        {
            "extension_id": non_recoverable_extension_id,
            "error_type": "MPTError",
            "message": "invalid extension configuration",
            "status_code": None,
        },
    ]
    assert ctx.installation_state.handled is False
    ctx.logger.error.assert_not_called()


async def test_pipeline_raises_unexpected_error(installation_context, mocker, pipeline):
    extension_service = installation_context.mpt_api_service.extensions
    extension_service.get_by_id = mocker.AsyncMock(side_effect=RuntimeError("broken"))

    with pytest.raises(RuntimeError, match="broken"):
        await pipeline.execute(installation_context)


@pytest.fixture
def failing_installation_context(installation_context, mocker):
    installation_context.mpt_api_service.extensions.get_by_id = mocker.AsyncMock(
        side_effect=MPTError("invalid"),
    )
    return installation_context


@pytest.fixture
def notify_mock(mocker):
    return mocker.patch(
        "mpt_installation_extension.pipelines.agreement_installation."
        "notify_non_recoverable_failure",
    )


async def test_pipeline_notifies(failing_installation_context, notify_mock, pipeline):
    with pytest.raises(FailError):
        await pipeline.execute(failing_installation_context)

    notify_mock.assert_called_once_with(failing_installation_context)


async def test_pipeline_fails_task(failing_installation_context, notify_mock, pipeline):
    with pytest.raises(FailError) as error:
        await pipeline.execute(failing_installation_context)

    assert str(error.value) == "One or more extension installations failed permanently"


async def test_pipeline_notifies_once(failing_installation_context, notify_mock, pipeline):
    ctx = failing_installation_context
    with pytest.raises(FailError):
        await pipeline.execute(ctx)

    await pipeline.on_step_succeeded(pipeline.steps[0], ctx)  # act

    notify_mock.assert_called_once_with(ctx)


async def test_pipeline_handles_action_once(failing_installation_context, notify_mock, pipeline):
    ctx = failing_installation_context
    with pytest.raises(FailError):
        await pipeline.execute(ctx)

    await pipeline.on_step_succeeded(pipeline.steps[0], ctx)  # act

    assert ctx.logger.error.call_count == 1


async def test_pipeline_skips_without_config(agreement_context_factory, pipeline):
    ctx = agreement_context_factory(context_type="installation", product_id="PRD-NOT-CONFIGURED")

    await pipeline.execute(ctx)  # act

    assert ctx.mpt_api_service.installations.create.call_count == 0


@pytest.mark.parametrize(
    ("create_error", "expected_outcome", "expected_message"),
    [
        (
            None,
            InstallationOutcome.CREATED,
            "Created installation INS-1 of extension {extension_id} for account ACC-CLIENT",
        ),
        (
            HTTPStatus.CONFLICT,
            InstallationOutcome.ALREADY_EXISTS,
            "Installation of extension {extension_id} for account ACC-CLIENT already exists",
        ),
    ],
)
async def test_pipeline_records_outcome(  # noqa: WPS211
    installation_context,
    make_mpt_error,
    mocker,
    pipeline,
    create_error,
    expected_outcome,
    expected_message,
):
    installation_context.mpt_api_service.extensions.get_by_id = mocker.AsyncMock(
        return_value=mocker.Mock(spec_set=["modules"], modules=[])
    )
    installation_context.mpt_api_service.installations.create = mocker.AsyncMock(
        return_value=mocker.Mock(spec_set=["id"], id="INS-1"),
        side_effect=create_error and make_mpt_error(create_error, "Conflict"),
    )

    await pipeline.execute(installation_context)  # act

    assert set(installation_context.installation_state.installations) == {
        InstallationResult(
            "EXT-1111", expected_outcome, expected_message.format(extension_id="EXT-1111")
        ),
        InstallationResult(
            "EXT-2222", expected_outcome, expected_message.format(extension_id="EXT-2222")
        ),
    }


async def test_pipeline_records_permanent_failure(
    failing_installation_context, notify_mock, pipeline
):
    with pytest.raises(FailError):
        await pipeline.execute(failing_installation_context)

    assert set(failing_installation_context.installation_state.installations) == {
        InstallationResult(
            "EXT-1111",
            InstallationOutcome.FAILED,
            "Installation of extension EXT-1111 for account ACC-CLIENT failed permanently: invalid",
        ),
        InstallationResult(
            "EXT-2222",
            InstallationOutcome.FAILED,
            "Installation of extension EXT-2222 for account ACC-CLIENT failed permanently: invalid",
        ),
    }


async def test_pipeline_records_retry(installation_context, mocker, pipeline):
    ctx = installation_context
    retry_error = MPTMaxRetryError("Marketplace request", 3)
    ctx.mpt_api_service.extensions.get_by_id = mocker.AsyncMock(side_effect=retry_error)

    with pytest.raises(DeferError):
        await pipeline.execute(ctx)

    assert set(ctx.installation_state.installations) == {
        InstallationResult(
            "EXT-1111",
            InstallationOutcome.RETRY,
            "Installation of extension EXT-1111 for account ACC-CLIENT "
            f"failed and will be retried: {retry_error}",
        ),
        InstallationResult(
            "EXT-2222",
            InstallationOutcome.RETRY,
            "Installation of extension EXT-2222 for account ACC-CLIENT "
            f"failed and will be retried: {retry_error}",
        ),
    }
