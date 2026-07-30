import pytest
from mpt_extension_sdk.api.auth.context import AccountType

from mpt_installation_extension.migrations.mixins.mpt_api_service import MPTAPIServiceMixin

MODULE = "mpt_installation_extension.migrations.mixins.mpt_api_service"


@pytest.fixture
def mixin():
    return MPTAPIServiceMixin()


def test_mpt_api_service_uses_ops_account(mixin, mocker):
    mocker.patch(
        f"{MODULE}.get_runtime_settings",
        return_value=mocker.Mock(extension_id="EXT-1", mpt_api_base_url="https://api.test"),
    )
    mocker.patch(
        f"{MODULE}.get_migration_settings",
        return_value=mocker.Mock(operations_account_id="ACC-OPS"),
    )
    provider = mocker.patch(f"{MODULE}.AccountTokenProvider", return_value=mocker.sentinel.provider)
    build = mocker.patch(
        f"{MODULE}.build_account_scoped_mpt_client", return_value=mocker.sentinel.client
    )
    service = mocker.patch(f"{MODULE}.MPTAPIService", return_value=mocker.sentinel.service)

    result = mixin.mpt_api_service

    assert result is mocker.sentinel.service
    service.assert_called_once_with(mocker.sentinel.client)
    build.assert_called_once_with(
        base_url="https://api.test", token_provider=mocker.sentinel.provider
    )
    auth = provider.call_args.kwargs["auth"]
    assert auth.account.id == "ACC-OPS"
    assert auth.account.type == AccountType.OPERATIONS
    assert auth.extension_id == "EXT-1"
