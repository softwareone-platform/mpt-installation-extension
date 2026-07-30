from typing import Any, cast, override

from mpt_api_client import RQLQuery
from mpt_api_client.resources.commerce.agreements import AsyncAgreementsService
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService as BaseMPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import (
    AgreementService as BaseAgreementService,
)
from mpt_extension_sdk.services.mpt_api_service.installation import (
    InstallationService as BaseInstallationService,
)


class AgreementService(BaseAgreementService):
    """Agreement service extended with reconciliation queries."""

    async def active_account_ids(self, product_id: str) -> list[str]:
        """Return the distinct client account ids with an active agreement of the product."""
        page = self._active_agreements(product_id)
        account_ids: set[str] = set()
        async for agreement in page.iterate(batch_size=100):
            account_ids.add(cast(Any, agreement.client).id)
        return list(account_ids)

    def _active_agreements(self, product_id: str) -> AsyncAgreementsService:
        active_status = RQLQuery(status="Active")
        query = active_status & RQLQuery().product.id.in_([product_id])
        return self._client.commerce.agreements.filter(query).select("client", "product")


class InstallationService(BaseInstallationService):
    """Installation service extended with reconciliation queries."""

    async def accounts_with_extension(self, extension_id: str) -> set[str]:
        """Return the account ids that already have an installation of the extension.

        Installations without an account (for example ``Expired`` ones) are excluded
        server-side, so every returned installation exposes ``account.id``.
        """
        installations = self._client.integration.installations
        query = RQLQuery(extension__id=extension_id)
        query &= RQLQuery().account.id.null(value=False)
        page = installations.filter(query).select("account")
        account_ids: set[str] = set()
        async for installation in page.iterate(batch_size=100):
            account_ids.add(cast(Any, installation.account).id)
        return account_ids


class MPTAPIService(BaseMPTAPIService):
    """MPT API service wired with the extension's extended agreement and installation services."""

    agreements: AgreementService  # type: ignore[mutable-override]
    installations: InstallationService  # type: ignore[mutable-override]

    @override
    def __init__(self, client: AsyncMPTClient) -> None:
        super().__init__(client)
        self.agreements = AgreementService(client)
        self.installations = InstallationService(client)
