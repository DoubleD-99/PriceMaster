"""Общие ошибки API и формат ответов (SDD 6.2, B-08)."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}


def error_payload(
    error_code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": str(message),
        "details": details or {},
    }


def error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(error_code, message, details),
        headers=headers,
    )


STATUS_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}
