from http import HTTPStatus

import pytest
from mpt_api_client.exceptions import MPTAPIError, MPTError, MPTHttpError, MPTMaxRetryError
from mpt_extension_sdk.errors.pipeline import DeferError
from mpt_extension_sdk.errors.step import DeferStepError
from mpt_extension_sdk.models import Installation

from mpt_installation_extension.pipelines.agreement_installation import (
    AgreementInstallationPipeline,
)
from mpt_installation_extension.pipelines.context import InstallationActionType


@pytest.fixture
def pipeline():
    return AgreementInstallationPipeline()


@pytest.fixture
def installation_context(agreement_context_factory):
    return agreement_context_factory(context_type="installation")


async def test_pipeline_creates_installations(installation_context, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    created_installations = []
    extension_response = mocker.Mock(
        spec_set=["modules"],
        modules=[
            mocker.Mock(spec_set=["id"], id="MOD-1"),
            mocker.Mock(spec_set=["id"], id="MOD-2"),
        ],
    )
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
    extension_service.get_by_id = mocker.AsyncMock(return_value=extension_response)
    installation_service.create = mocker.AsyncMock(
        side_effect=created_installations.append,
    )

    await pipeline.execute(installation_context)  # act

    assert installation_service.exists_for_account.await_args_list == [
        mocker.call(extension_id="EXT-1111", account_id="ACC-CLIENT"),
        mocker.call(extension_id="EXT-2222", account_id="ACC-CLIENT"),
    ]
    assert isinstance(created_installations[0], Installation)
    assert [module.id for module in created_installations[0].modules] == ["MOD-1", "MOD-2"]


async def test_pipeline_skips_existing_installations(installation_context, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=True)
    extension_service.get_by_id = mocker.AsyncMock()
    installation_service.create = mocker.AsyncMock()

    await pipeline.execute(installation_context)  # act

    extension_service.get_by_id.assert_not_awaited()
    installation_service.create.assert_not_awaited()


async def test_pipeline_skips_concurrent_existing(installation_context, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    extension_response = mocker.Mock(
        spec_set=["modules"],
        modules=[mocker.Mock(spec_set=["id"], id="MOD-1")],
    )
    exists_for_account_mock = mocker.AsyncMock()
    exists_for_account_mock.return_value = False
    installation_service.exists_for_account = exists_for_account_mock
    extension_service.get_by_id = mocker.AsyncMock(return_value=extension_response)
    installation_service.create = mocker.AsyncMock(
        side_effect=[
            MPTAPIError(
                HTTPStatus.CONFLICT,
                "Conflict",
                {"status": str(HTTPStatus.CONFLICT), "title": "Conflict"},
            ),
            None,
        ],
    )

    await pipeline.execute(installation_context)  # act

    assert installation_context.installation_state.action is None
    assert installation_service.create.await_count == 2


async def test_pipeline_defers_after_http_error(installation_context, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=MPTHttpError(
            HTTPStatus.SERVICE_UNAVAILABLE, "Service unavailable", "unavailable"
        ),
    )
    installation_service.create = mocker.AsyncMock()

    with pytest.raises(DeferError) as error:
        await pipeline.execute(installation_context)

    assert error.value.delay_seconds == DeferStepError().delay_seconds


async def test_pipeline_defers_after_max_retry_error(installation_context, mocker, pipeline):
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=MPTMaxRetryError("Marketplace request", 3),
    )
    installation_service.create = mocker.AsyncMock()

    with pytest.raises(DeferError) as error:
        await pipeline.execute(installation_context)

    assert error.value.delay_seconds == DeferStepError().delay_seconds


async def test_pipeline_records_failure_action(installation_context, mocker, pipeline):
    ctx = installation_context
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=MPTAPIError(
            HTTPStatus.NOT_FOUND,
            "Not found",
            {"status": str(HTTPStatus.NOT_FOUND), "title": "Not found"},
        ),
    )
    installation_service.create = mocker.AsyncMock()

    await pipeline.execute(ctx)  # act

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
    assert ctx.installation_state.action.target == (
        InstallationActionType.NOTIFY_NON_RECOVERABLE_FAILURE
    )
    assert ctx.installation_state.handled is True


async def test_pipeline_records_action_and_defers(installation_context, mocker, pipeline):
    ctx = installation_context
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
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
    installation_service.create = mocker.AsyncMock()

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
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=RuntimeError("broken"),
    )
    installation_service.create = mocker.AsyncMock()

    with pytest.raises(RuntimeError, match="broken"):
        await pipeline.execute(installation_context)


async def test_pipeline_handles_action_once(installation_context, mocker, pipeline):
    ctx = installation_context
    installation_service = installation_context.mpt_api_service.installations
    extension_service = installation_context.mpt_api_service.extensions
    installation_service.exists_for_account = mocker.AsyncMock(return_value=False)
    extension_service.get_by_id = mocker.AsyncMock(
        side_effect=MPTError("invalid"),
    )
    installation_service.create = mocker.AsyncMock()
    await pipeline.execute(ctx)

    await pipeline.on_step_succeeded(pipeline.steps[0], ctx)  # act

    assert ctx.logger.error.call_count == 1


async def test_pipeline_skips_without_config(agreement_context_factory, pipeline):
    ctx = agreement_context_factory(context_type="installation", product_id="PRD-NOT-CONFIGURED")

    await pipeline.execute(ctx)  # act

    assert ctx.mpt_api_service.installations.exists_for_account.call_count == 0
