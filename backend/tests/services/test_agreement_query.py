import pytest

from mpt_installation_extension.services.agreement_query import AgreementQueryService


@pytest.fixture
def make_agreements(mocker):
    def factory(account_ids):
        agreements = [mocker.Mock(client=mocker.Mock(id=account_id)) for account_id in account_ids]
        collection = mocker.MagicMock(spec_set=["filter", "select", "iterate"])
        collection.filter.return_value = collection
        collection.select.return_value = collection
        collection.iterate.return_value.__aiter__.return_value = agreements
        return collection

    return factory


@pytest.fixture
def mpt_api_service(mocker):
    return mocker.Mock(spec_set=["client"])


@pytest.fixture
def service(mpt_api_service):
    return AgreementQueryService(mpt_api_service)


async def test_active_account_ids_returns_distinct(service, mpt_api_service, make_agreements):
    mpt_api_service.client.commerce.agreements = make_agreements(["ACC-1", "ACC-2", "ACC-1"])

    result = await service.active_account_ids("PRD-1")

    assert sorted(result) == ["ACC-1", "ACC-2"]


async def test_active_account_ids_empty(service, mpt_api_service, make_agreements):
    mpt_api_service.client.commerce.agreements = make_agreements([])

    result = await service.active_account_ids("PRD-1")

    assert result == []


async def test_active_account_ids_skips_missing_client(
    service, mpt_api_service, make_agreements, mocker
):
    collection = make_agreements(["ACC-1"])
    without_client = mocker.Mock(client=None)
    with_client = mocker.Mock(client=mocker.Mock(id="ACC-1"))
    collection.iterate.return_value.__aiter__.return_value = [without_client, with_client]
    mpt_api_service.client.commerce.agreements = collection

    result = await service.active_account_ids("PRD-1")

    assert result == ["ACC-1"]
