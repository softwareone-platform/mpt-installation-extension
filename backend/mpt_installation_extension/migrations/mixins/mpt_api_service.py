from functools import cached_property

from mpt_extension_sdk.api.auth.context import Account, AccountType, AuthContext
from mpt_extension_sdk.services.mpt_api_service.account_scoped_client import (
    AccountTokenProvider,
    build_account_scoped_mpt_client,
)
from mpt_extension_sdk.settings.runtime import get_runtime_settings

from mpt_installation_extension.services.mpt_api_service import MPTAPIService
from mpt_installation_extension.settings import get_migration_settings


class MPTAPIServiceMixin:
    """Expose an operations-scoped MPT API service to migrations.

    The token is minted from the extension's own API key (`SDK_EXTENSION_API_KEY`)
    for the operations account, so no per-account token is stored in the extension.
    """

    @cached_property
    def mpt_api_service(self) -> MPTAPIService:
        """Operations-scoped MPT API service, created on first access."""
        runtime = get_runtime_settings()
        auth = AuthContext(
            token="",
            account=Account(
                id=get_migration_settings().operations_account_id,
                type=AccountType.OPERATIONS,
            ),
            permissions={},
            extension_id=runtime.extension_id,
        )
        token_provider = AccountTokenProvider(
            runtime_settings=runtime, auth=auth, service_type=MPTAPIService
        )
        client = build_account_scoped_mpt_client(
            base_url=runtime.mpt_api_base_url, token_provider=token_provider
        )
        return MPTAPIService(client)
