from mpt_extension_sdk import ExtensionApp

from mpt_installation_extension.routers.events.agreements import router as agreements_router
from mpt_installation_extension.services.mpt_api_service import MPTAPIService

ext_app = ExtensionApp(prefix="", version="6.0.0", mpt_api_service_type=MPTAPIService)
ext_app.include_router(agreements_router)
