from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


def error_payload(
    *,
    detail: str,
    error_code: str,
    resource: str | None = None,
    resource_id: int | str | None = None,
    errors: list[dict[str, Any]] | list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "detail": detail,
        "error_code": error_code,
    }
    if resource is not None:
        payload["resource"] = resource
    if resource_id is not None:
        payload["resource_id"] = resource_id
    if errors is not None:
        payload["errors"] = errors
    if extra:
        payload.update(extra)
    return payload


def http_error(
    *,
    status_code: int,
    detail: str,
    error_code: str,
    resource: str | None = None,
    resource_id: int | str | None = None,
    errors: list[dict[str, Any]] | list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=error_payload(
            detail=detail,
            error_code=error_code,
            resource=resource,
            resource_id=resource_id,
            errors=errors,
            extra=extra,
        ),
    )


def not_found(resource: str, resource_id: int | str | None = None) -> HTTPException:
    suffix = f" with id {resource_id}" if resource_id is not None else ""
    label = resource.replace("_", " ")
    return http_error(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{label.capitalize()}{suffix} was not found",
        error_code=f"{resource.upper()}_NOT_FOUND",
        resource=resource,
        resource_id=resource_id,
    )


def bad_request(
    detail: str,
    *,
    error_code: str = "BAD_REQUEST",
    resource: str | None = None,
    resource_id: int | str | None = None,
    errors: list[dict[str, Any]] | list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> HTTPException:
    return http_error(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
        error_code=error_code,
        resource=resource,
        resource_id=resource_id,
        errors=errors,
        extra=extra,
    )


def forbidden(detail: str, *, error_code: str = "FORBIDDEN", extra: dict[str, Any] | None = None) -> HTTPException:
    return http_error(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
        error_code=error_code,
        extra=extra,
    )


def unauthorized(
    detail: str,
    *,
    error_code: str = "UNAUTHORIZED",
    resource: str | None = None,
    resource_id: int | str | None = None,
) -> HTTPException:
    return http_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        error_code=error_code,
        resource=resource,
        resource_id=resource_id,
    )


def conflict(
    detail: str,
    *,
    error_code: str = "CONFLICT",
    resource: str | None = None,
    resource_id: int | str | None = None,
) -> HTTPException:
    return http_error(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
        error_code=error_code,
        resource=resource,
        resource_id=resource_id,
    )
