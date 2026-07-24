from mpt_api_client import RQLQuery
from mpt_api_client.resources.commerce.agreements import AsyncAgreementsService
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService


class AgreementQueryService:
    """Query Marketplace agreements."""

    def __init__(self, mpt_api_service: MPTAPIService) -> None:
        self._mpt = mpt_api_service

    async def active_account_ids(self, product_id: str) -> list[str]:
        """Return the distinct client account ids with an active agreement of the product."""
        page = self._active_agreements(product_id)
        account_ids: set[str] = set()
        async for agreement in page.iterate(batch_size=100):
            client = agreement.client
            if client is not None:
                account_ids.add(client.id)
        return list(account_ids)

    def _active_agreements(self, product_id: str) -> AsyncAgreementsService:
        active_status = RQLQuery(status="Active")
        query = active_status & RQLQuery().product.id.in_([product_id])
        client = self._mpt.client
        return client.commerce.agreements.filter(query).select("client", "product")
