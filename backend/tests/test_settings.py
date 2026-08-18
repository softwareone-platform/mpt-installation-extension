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


def test_loads_teams_settings(monkeypatch):
    monkeypatch.setenv("EXT_MSTEAMS_WEBHOOK_URL", "https://webhook.example.test/teams")
    monkeypatch.setenv("EXT_MSTEAMS_NOTIFICATIONS_ENABLED", "true")

    result = ExtensionSettings.load()

    assert result.teams_webhook_url == "https://webhook.example.test/teams"
    assert result.teams_notifications_enabled is True


def test_teams_settings_default_to_disabled(monkeypatch):
    monkeypatch.delenv("EXT_MSTEAMS_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("EXT_MSTEAMS_NOTIFICATIONS_ENABLED", raising=False)

    result = ExtensionSettings.load()

    assert result.teams_webhook_url is None
    assert result.teams_notifications_enabled is False


def test_migration_settings_loads_ops_account(monkeypatch):
    monkeypatch.setenv("EXT_OPERATIONS_ACCOUNT_ID", "ACC-OPS")

    result = MigrationExtensionSettings.load()

    assert result.operations_account_id == "ACC-OPS"


def test_migration_settings_requires_ops_account(monkeypatch):
    monkeypatch.delenv("EXT_OPERATIONS_ACCOUNT_ID", raising=False)

    with pytest.raises(ConfigError, match="EXT_OPERATIONS_ACCOUNT_ID"):
        MigrationExtensionSettings.load()
