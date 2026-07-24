from http import HTTPStatus

import pytest
from mpt_api_client.exceptions import MPTAPIError
from mpt_extension_sdk.models import Installation

from mpt_installation_extension.services.extension_installation import (
    ExtensionInstallationCreatorService,
    InstallOutcome,
)


@pytest.fixture
def make_extension(mocker):
    def factory(module_ids):
        return mocker.Mock(
            spec_set=["modules"],
            modules=[mocker.Mock(spec_set=["id"], id=module_id) for module_id in module_ids],
        )

    return factory


@pytest.fixture
def mpt_api_service(mocker, make_extension):
    service = mocker.Mock(spec_set=["extensions", "installations"])
    service.extensions = mocker.Mock(spec_set=["get_by_id"])
    service.extensions.get_by_id = mocker.AsyncMock(return_value=make_extension(["MOD-1"]))
    service.installations = mocker.Mock(spec_set=["create"])
    service.installations.create = mocker.AsyncMock()
    return service


@pytest.fixture
def agreement_query(mocker):
    query = mocker.Mock(spec_set=["active_account_ids"])
    query.active_account_ids = mocker.AsyncMock(return_value=["ACC-1"])
    return query


@pytest.fixture
def service(mpt_api_service, agreement_query):
    return ExtensionInstallationCreatorService(mpt_api_service, agreement_query)


async def test_create_installs_with_modules(service, mpt_api_service, make_extension, mocker):
    mpt_api_service.extensions.get_by_id = mocker.AsyncMock(
        return_value=make_extension(["MOD-1", "MOD-2"])
    )
    created = []
    mpt_api_service.installations.create = mocker.AsyncMock(side_effect=created.append)

    result = await service.create_installation(account_id="ACC-1", extension_id="EXT-1")

    assert result == InstallOutcome.CREATED
    assert isinstance(created[0], Installation)
    assert created[0].account.id == "ACC-1"
    assert created[0].extension.id == "EXT-1"
    assert [module.id for module in created[0].modules] == ["MOD-1", "MOD-2"]


async def test_create_skips_on_conflict(service, mpt_api_service, make_mpt_error, mocker):
    mpt_api_service.installations.create = mocker.AsyncMock(
        side_effect=make_mpt_error(HTTPStatus.CONFLICT, "Conflict")
    )

    result = await service.create_installation(account_id="ACC-1", extension_id="EXT-1")

    assert result == InstallOutcome.ALREADY_EXISTS


async def test_create_propagates_other_errors(service, mpt_api_service, make_mpt_error, mocker):
    mpt_api_service.installations.create = mocker.AsyncMock(
        side_effect=make_mpt_error(HTTPStatus.NOT_FOUND, "Not found")
    )

    with pytest.raises(MPTAPIError):
        await service.create_installation(account_id="ACC-1", extension_id="EXT-1")


async def test_missing_installs_for_each_account(service, mpt_api_service, agreement_query, mocker):
    agreement_query.active_account_ids = mocker.AsyncMock(return_value=["ACC-1", "ACC-2"])

    result = await service.create_missing_installations({"PRD-1": ["EXT-1"]})

    assert result.created == 2
    assert result.already_exists == 0
    assert result.failures == []
    agreement_query.active_account_ids.assert_awaited_once_with("PRD-1")
    # get_by_id is cached once per extension, not per account.
    mpt_api_service.extensions.get_by_id.assert_awaited_once_with("EXT-1")
    assert mpt_api_service.installations.create.await_count == 2


async def test_missing_counts_conflicts(service, mpt_api_service, make_mpt_error, mocker):
    mpt_api_service.installations.create = mocker.AsyncMock(
        side_effect=make_mpt_error(HTTPStatus.CONFLICT, "Conflict")
    )

    result = await service.create_missing_installations({"PRD-1": ["EXT-1"]})

    assert result.created == 0
    assert result.already_exists == 1
    assert result.failures == []


async def test_missing_aggregates_failures(
    service, mpt_api_service, agreement_query, make_mpt_error, mocker
):
    agreement_query.active_account_ids = mocker.AsyncMock(return_value=["ACC-1", "ACC-2"])
    mpt_api_service.installations.create = mocker.AsyncMock(
        side_effect=[make_mpt_error(HTTPStatus.NOT_FOUND, "Not found"), None]
    )

    result = await service.create_missing_installations({"PRD-1": ["EXT-1"]})

    assert result.created == 1
    assert len(result.failures) == 1
    assert result.failures[0].extension_id == "EXT-1"
    assert mpt_api_service.installations.create.await_count == 2
