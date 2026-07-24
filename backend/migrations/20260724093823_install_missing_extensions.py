import asyncio
from typing import override

from mpt_tool.migration import DataBaseMigration

from mpt_installation_extension.migrations.mixins.mpt_api_service import MPTAPIServiceMixin
from mpt_installation_extension.services.extension_installation import (
    ExtensionInstallationCreatorService,
)
from mpt_installation_extension.settings import get_extension_settings


class Migration(MPTAPIServiceMixin, DataBaseMigration):
    """Install the configured extensions on clients with active agreements that lack them."""

    @override
    def run(self) -> None:
        """Reconcile installations for the current product-to-extension mapping."""
        service = ExtensionInstallationCreatorService(self.mpt_api_service)
        targets = get_extension_settings().product_extension_mapping
        report = asyncio.run(service.create_missing_installations(targets))
        self.log.info(
            "Installation backfill finished: created=%s already_exists=%s failed=%s",
            report.created,
            report.already_exists,
            len(report.failures),
        )
        if report.failures:
            raise RuntimeError(f"{len(report.failures)} installations failed: {report.failures}")
