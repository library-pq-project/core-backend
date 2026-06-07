import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    origins = [
        "http://localhost:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.on_event("startup")
    async def startup_warning() -> None:
        if settings.PROTOTYPE_MODE:
            logger.warning(
                "WARNING: AUTHORIZATION BYPASSED - PROTOTYPE MODE ENABLED (user_id=%s role=%s)",
                settings.PROTOTYPE_USER_ID,
                settings.PROTOTYPE_USER_ROLE,
            )

    return app


app = create_app()
