"""Middleware: request id and tenant/auth checks (JWT + X-Store-ID)."""

import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.app.api.errors import error_response
from backend.app.core.security import AuthError, TokenPayload, decode_access_token

logger = logging.getLogger(__name__)

PUBLIC_PATHS = ("/auth/login", "/docs", "/redoc", "/openapi.json", "/health")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """Проверяет токен на приватных маршрутах и согласует X-Store-ID."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path.startswith(PUBLIC_PATHS):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return error_response(
                status_code=401,
                error_code="UNAUTHORIZED",
                message="Требуется Authorization: Bearer <token>",
            )

        try:
            payload: TokenPayload = decode_access_token(
                authorization.removeprefix("Bearer ")
            )
        except AuthError as exc:
            logger.info(
                "auth failed",
                extra={"request_id": getattr(request.state, "request_id", None)},
            )
            return error_response(
                status_code=401,
                error_code="UNAUTHORIZED",
                message=str(exc),
            )

        store_header = request.headers.get("X-Store-ID")
        if store_header is not None:
            try:
                store_id = int(store_header)
            except ValueError:
                return error_response(
                    status_code=400,
                    error_code="INVALID_STORE_ID",
                    message="X-Store-ID должен быть целым числом",
                )
            if store_id not in payload.store_ids:
                return error_response(
                    status_code=403,
                    error_code="STORE_FORBIDDEN",
                    message="Магазин не входит в список доступных для токена",
                )

        request.state.user = payload
        return await call_next(request)
