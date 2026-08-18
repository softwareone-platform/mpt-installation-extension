import pytest

from mpt_installation_extension.services.mpt_api_service import (
    AgreementService,
    InstallationService,
)


@pytest.fixture
def collection(mocker):
    def factory(records):
        page = mocker.MagicMock(spec_set=["filter", "select", "iterate"])
        page.filter.return_value = page
        page.select.return_value = page
        page.iterate.return_value.__aiter__.return_value = records
        return page

    return factory


async def test_agreements_active_account_ids_dedup(mocker, collection):
    client = mocker.Mock()
    agreements = collection([
        mocker.Mock(client=mocker.Mock(id="ACC-1")),
        mocker.Mock(client=mocker.Mock(id="ACC-2")),
        mocker.Mock(client=mocker.Mock(id="ACC-1")),
    ])
    client.commerce.agreements = agreements

    result = await AgreementService(client).active_account_ids("PRD-1")

    assert sorted(result) == ["ACC-1", "ACC-2"]
    assert (
        str(agreements.filter.call_args.args[0])
        == "and(eq(status,'Active'),in(product.id,('PRD-1')))"
    )
    agreements.select.assert_called_once_with("client", "product")


async def test_installations_accounts_with_extension(mocker, collection):
    client = mocker.Mock()
    installations = collection([
        mocker.Mock(account=mocker.Mock(id="ACC-1")),
        mocker.Mock(account=mocker.Mock(id="ACC-2")),
        mocker.Mock(account=mocker.Mock(id="ACC-1")),
    ])
    client.integration.installations = installations

    result = await InstallationService(client).accounts_with_extension("EXT-1")

    assert result == {"ACC-1", "ACC-2"}
    assert (
        str(installations.filter.call_args.args[0])
        == "and(eq(extension.id,'EXT-1'),ne(account.id,null()))"
    )
    installations.select.assert_called_once_with("account")
