from functools import cached_property

from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_tool.config import get_mpt_config


class MPTAPIServiceMixin:
    """Mixin to add the MPT API service to migrations.

    MPT API token and base URL are read from the environment variables MPT_API_TOKEN
    and MPT_API_BASE_URL.
    """

    @cached_property
    def mpt_api_service(self) -> MPTAPIService:
        """MPT API service from environment configuration, created on first access.

        Raises:
            ValueError: If required environment variables are not set.
        """
        api_token = get_mpt_config("api_token")
        base_url = get_mpt_config("base_url")
        if not api_token or not base_url:
            raise ValueError("MPT API token and base URL must be set in env variables")
        return MPTAPIService.from_config(base_url, api_token)
