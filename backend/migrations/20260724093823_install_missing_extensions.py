import asyncio
from typing import override

from mpt_tool.migration import DataBaseMigration

from mpt_installation_extension.migrations.mixins.mpt_api_service import MPTAPIServiceMixin
from mpt_installation_extension.services.extension_installation import (
    ExtensionInstallationCreatorService,
)
from mpt_installation_extension.settings import get_migration_settings


class Migration(MPTAPIServiceMixin, DataBaseMigration):
    """Install the configured extensions on clients with active agreements that lack them."""

    @override
    def run(self) -> None:
        """Reconcile installations for the current product-to-extension mapping."""
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        service = ExtensionInstallationCreatorService(self.mpt_api_service)
        report = await service.create_missing_installations(
            get_migration_settings().product_extension_mapping
        )
        self.log.info(
            "Installation backfill finished: created=%s already_exists=%s failed=%s",
            report.created,
            report.already_exists,
            len(report.failures),
        )
        if report.failures:
            self.log.error(
                "%s installations failures during the migration: %s",
                len(report.failures),
                report.failures,
            )
