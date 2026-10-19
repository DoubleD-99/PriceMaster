"""TenantMiddleware — единая точка проверки JWT и изоляции по магазинам.

SDD, раздел 3.4 / ADR-04: middleware извлекает store_id из заголовка
X-Store-ID и токена; несовпадение -> 403 Forbidden. Payload токена
({ sub, store_ids }) кладётся в request.state.user и читается зависимостью
get_current_user (api/deps.py).

Публичные маршруты (без JWT): POST /auth/login, /docs, /redoc,
/openapi.json, /health.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.app.core.security import AuthError, TokenPayload, decode_access_token

# Маршруты, доступные без Authorization: Bearer
PUBLIC_PATHS = ("/auth/login", "/docs", "/redoc", "/openapi.json", "/health")


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


class TenantMiddleware(BaseHTTPMiddleware):
    """Проверяет токен на всех приватных маршрутах и согласует X-Store-ID."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path.startswith(PUBLIC_PATHS):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return _error(401, "Отсутствует Authorization: Bearer <Token>")

        try:
            payload: TokenPayload = decode_access_token(
                authorization.removeprefix("Bearer ")
            )
        except AuthError as exc:
            return _error(401, str(exc))

        store_header = request.headers.get("X-Store-ID")
        if store_header is not None:
            try:
                store_id = int(store_header)
            except ValueError:
                return _error(400, "X-Store-ID должен быть целым числом")
            if store_id not in payload.store_ids:
                return _error(403, "Магазин не входит в список доступных для токена")

        request.state.user = payload
        return await call_next(request)
