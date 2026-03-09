from fastapi import FastAPI

from src.api import api_router
from src.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
    )
    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app


app = create_app()
