import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed. Check the submitted fields and try again.",
                "errors": exc.errors(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=409,
            content={
                "detail": "The request conflicts with existing data. Check for duplicate values or invalid references.",
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("Database error on %s", request.url.path, exc_info=(type(exc), exc, exc.__traceback__))
        return JSONResponse(
            status_code=500,
            content={
                "detail": "The request could not be completed because of a database error.",
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s", request.url.path, exc_info=(type(exc), exc, exc.__traceback__))
        return JSONResponse(
            status_code=500,
            content={
                "detail": "The request could not be processed due to an unexpected server error.",
                "path": str(request.url.path),
            },
        )

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
