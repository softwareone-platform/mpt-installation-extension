import logging
import os

import pytest
from mpt_api_client.exceptions import MPTAPIError
from mpt_extension_sdk.models import Account, Agreement, Licensee, Product
from mpt_extension_sdk.pipeline import AgreementContext, EventMetadata
from mpt_extension_sdk.settings.runtime import RuntimeSettings

from mpt_installation_extension.pipelines.context import InstallationAgreementContext
from mpt_installation_extension.settings import ExtensionSettings

PRODUCT_EXTENSION_MAPPING = '{"PRD-1111":["EXT-1111","EXT-2222"]}'


@pytest.fixture
def make_mpt_error():
    def factory(status, title):
        return MPTAPIError(status, title, {"status": str(status), "title": title})

    return factory


os.environ.setdefault("EXT_MPT_PRODUCT_EXTENSION_MAPPING", PRODUCT_EXTENSION_MAPPING)


@pytest.fixture(autouse=True)
def extension_env(monkeypatch):
    monkeypatch.setenv("EXT_MPT_PRODUCT_EXTENSION_MAPPING", PRODUCT_EXTENSION_MAPPING)


@pytest.fixture
def agreement_context_factory(mocker):
    def factory(context_type="agreement", product_id="PRD-1111"):
        installation_service = mocker.Mock(spec_set=["create", "exists_for_account"])
        extension_service = mocker.Mock(spec_set=["get_by_id"])
        mpt_api_service = mocker.Mock(spec_set=["extensions", "installations"])
        mpt_api_service.extensions = extension_service
        mpt_api_service.installations = installation_service
        ctx = AgreementContext(
            logger=mocker.Mock(spec=logging.Logger),
            meta=EventMetadata(
                event_id="EVT-1", object_id="AGR-1", object_type="Agreement", task_id=""
            ),
            mpt_api_service=mpt_api_service,
            ext_settings=ExtensionSettings(
                product_extension_mapping={"PRD-1111": ["EXT-1111", "EXT-2222"]},
            ),
            runtime_settings=mocker.Mock(
                spec=RuntimeSettings,
                mpt_api_base_url="https://api.example.test",
                extension_id="EXT-1111-1111",
            ),
            agreement=Agreement(
                id="AGR-1",
                name="Agreement",
                status="Active",
                client=Account(id="ACC-CLIENT", name="Client"),
                licensee=Licensee(id="LIC-1", name="Licensee", status="Active"),
                product=Product(id=product_id, name="Product"),
            ),
        )
        if context_type == "installation":
            return InstallationAgreementContext.from_context(ctx)
        return ctx

    return factory
