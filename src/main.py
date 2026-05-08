import logging

from fastapi import FastAPI

from src.api import api_router
from src.core.config import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    env = settings.APP_ENV.lower().strip()
    if settings.PROTOTYPE_MODE and env in {"production", "prod"}:
        raise RuntimeError("PROTOTYPE_MODE cannot be enabled when APP_ENV=production")

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
    )
    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.on_event("startup")
    async def startup_warning() -> None:
        if settings.PROTOTYPE_MODE:
            logger.warning("!!! PROTOTYPE MODE ENABLED !!! Auth is bypassed using PROTOTYPE_USER_ID=%s", settings.PROTOTYPE_USER_ID)

    return app


app = create_app()
