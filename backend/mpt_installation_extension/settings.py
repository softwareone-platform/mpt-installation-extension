import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Self, override

from mpt_extension_sdk.settings.extension import BaseExtensionSettings


@dataclass(frozen=True)
class ExtensionSettings(BaseExtensionSettings):
    """Extension settings."""

    product_extension_mapping: dict[str, list[str]]

    @property
    def product_ids(self) -> tuple[str, ...]:
        """Configured Marketplace product ids."""
        return tuple(self.product_extension_mapping.keys())

    @property
    def product_ids_rql(self) -> str:
        """Configured Marketplace product ids formatted for RQL."""
        product_ids = ",".join(self.product_ids)
        return f"({product_ids})"

    @override
    @property
    def required_env_vars(self) -> list[tuple[Any, ...]]:
        return [
            (
                self.product_extension_mapping,
                "Product extension mapping is required (EXT_MPT_PRODUCT_EXTENSION_MAPPING)",
            ),
        ]

    @override
    @classmethod
    def load(cls) -> Self:
        return cls(
            product_extension_mapping=cls.json_env("EXT_MPT_PRODUCT_EXTENSION_MAPPING"),
        )


@dataclass(frozen=True)
class MigrationExtensionSettings(ExtensionSettings):
    """Extension settings for migrations, adding the operations account id."""

    operations_account_id: str = ""

    @override
    @property
    def required_env_vars(self) -> list[tuple[Any, ...]]:
        return [
            *super().required_env_vars,
            (
                self.operations_account_id,
                "Operations account id is required (EXT_OPERATIONS_ACCOUNT_ID)",
            ),
        ]

    @override
    @classmethod
    def load(cls) -> Self:
        return cls(
            product_extension_mapping=cls.json_env("EXT_MPT_PRODUCT_EXTENSION_MAPPING"),
            operations_account_id=os.getenv("EXT_OPERATIONS_ACCOUNT_ID", ""),
        )


@lru_cache(maxsize=1)
def get_extension_settings() -> ExtensionSettings:
    """Return a cached `ExtensionSettings` instance."""
    return ExtensionSettings.load()


@lru_cache(maxsize=1)
def get_migration_settings() -> MigrationExtensionSettings:
    """Return a cached `MigrationExtensionSettings` instance."""
    return MigrationExtensionSettings.load()
