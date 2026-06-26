from mpt_extension_sdk import ExtensionApp

from mpt_installation_extension.routers.events.agreements import router as agreements_router

ext_app = ExtensionApp(prefix="", version="6.0.0")
ext_app.include_router(agreements_router)
