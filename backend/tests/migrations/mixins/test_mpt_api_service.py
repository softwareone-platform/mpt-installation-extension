import pytest

from mpt_installation_extension.migrations.mixins.mpt_api_service import MPTAPIServiceMixin

MODULE = "mpt_installation_extension.migrations.mixins.mpt_api_service"


@pytest.fixture
def mixin():
    return MPTAPIServiceMixin()


def test_mpt_api_service_builds_from_env(mixin, mocker):
    mocker.patch(f"{MODULE}.get_mpt_config", side_effect=["token", "https://api.test"])
    from_config = mocker.patch(
        f"{MODULE}.MPTAPIService.from_config", return_value=mocker.sentinel.service
    )

    result = mixin.mpt_api_service

    assert result is mocker.sentinel.service
    from_config.assert_called_once_with("https://api.test", "token")


def test_mpt_api_service_raises_without_env(mixin, mocker):
    mocker.patch(f"{MODULE}.get_mpt_config", return_value=None)

    with pytest.raises(ValueError, match="must be set"):
        assert mixin.mpt_api_service
