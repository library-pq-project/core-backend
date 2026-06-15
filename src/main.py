import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status as http_status
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api import api_router
from src.core.config import settings

logger = logging.getLogger(__name__)


def _default_error_code(status_code: int) -> str:
    if status_code == http_status.HTTP_400_BAD_REQUEST:
        return "BAD_REQUEST"
    if status_code == http_status.HTTP_401_UNAUTHORIZED:
        return "UNAUTHORIZED"
    if status_code == http_status.HTTP_403_FORBIDDEN:
        return "FORBIDDEN"
    if status_code == http_status.HTTP_404_NOT_FOUND:
        return "NOT_FOUND"
    if status_code == http_status.HTTP_409_CONFLICT:
        return "CONFLICT"
    if status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY:
        return "VALIDATION_ERROR"
    if status_code >= 500:
        return "INTERNAL_SERVER_ERROR"
    return f"HTTP_{status_code}"


def _normalize_error_detail(detail: object, *, status_code: int, path: str) -> dict:
    if isinstance(detail, dict):
        payload = dict(detail)
    else:
        payload = {
            "detail": str(detail),
            "error_code": _default_error_code(status_code),
        }

    payload.setdefault("detail", "Request failed")
    payload.setdefault("error_code", _default_error_code(status_code))
    payload["path"] = path
    return payload


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

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_normalize_error_detail(exc.detail, status_code=exc.status_code, path=str(request.url.path)),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_normalize_error_detail(
                {
                    "detail": "Request validation failed. Check the submitted fields and try again.",
                    "error_code": "VALIDATION_ERROR",
                    "errors": exc.errors(),
                },
                status_code=422,
                path=str(request.url.path),
            ),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=409,
            content=_normalize_error_detail(
                {
                    "detail": "The request conflicts with existing data. Check for duplicate values or invalid references.",
                    "error_code": "DATA_CONFLICT",
                },
                status_code=409,
                path=str(request.url.path),
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("Database error on %s", request.url.path, exc_info=(type(exc), exc, exc.__traceback__))
        return JSONResponse(
            status_code=500,
            content=_normalize_error_detail(
                {
                    "detail": "The request could not be completed because of a database error.",
                    "error_code": "DATABASE_ERROR",
                },
                status_code=500,
                path=str(request.url.path),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s", request.url.path, exc_info=(type(exc), exc, exc.__traceback__))
        return JSONResponse(
            status_code=500,
            content=_normalize_error_detail(
                {
                    "detail": "The request could not be processed due to an unexpected server error.",
                    "error_code": "INTERNAL_SERVER_ERROR",
                },
                status_code=500,
                path=str(request.url.path),
            ),
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
