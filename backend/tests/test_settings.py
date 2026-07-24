import pytest
from mpt_extension_sdk.errors.runtime import ConfigError

from mpt_installation_extension.settings import ExtensionSettings, MigrationExtensionSettings


def test_loads_product_extension_mapping():
    expected_mapping = {
        "PRD-1111": ["EXT-1111", "EXT-2222"],
    }

    result = ExtensionSettings.load()

    assert result.product_extension_mapping == expected_mapping
    assert result.product_ids == ("PRD-1111",)
    assert result.product_ids_rql == "(PRD-1111)"


def test_migration_settings_loads_ops_account(monkeypatch):
    monkeypatch.setenv("EXT_OPERATIONS_ACCOUNT_ID", "ACC-OPS")

    result = MigrationExtensionSettings.load()

    assert result.operations_account_id == "ACC-OPS"


def test_migration_settings_requires_ops_account(monkeypatch):
    monkeypatch.delenv("EXT_OPERATIONS_ACCOUNT_ID", raising=False)

    with pytest.raises(ConfigError, match="EXT_OPERATIONS_ACCOUNT_ID"):
        MigrationExtensionSettings.load()
