"""Входная точка FastAPI-приложения."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.errors import STATUS_ERROR_CODES, ApiError, error_response
from backend.app.api.middleware import RequestIdMiddleware, TenantMiddleware
from backend.app.api.v1 import (
    analytics,
    auth,
    barcodes,
    inventory,
    products,
    recommendations,
    stores,
    wms,
)

logger = logging.getLogger(__name__)

TAGS_METADATA = [
    {"name": "Аутентификация", "description": "Вход и выдача JWT."},
    {"name": "Магазины", "description": "Доступные магазины пользователя."},
    {"name": "Товары", "description": "Каталог товаров."},
    {"name": "Штрихкоды", "description": "Поиск товара по штрихкоду."},
    {"name": "Остатки", "description": "Партии остатков и алерты."},
    {"name": "WMS", "description": "Приёмка и списание по FIFO."},
    {"name": "Рекомендации", "description": "AI-рекомендации и решение владельца."},
    {"name": "Аналитика", "description": "Агрегация продаж для графиков."},
    {"name": "Сервис", "description": "Проверки доступности."},
]

app = FastAPI(
    title="PriceMaster API",
    description=(
        "API системы агентного динамического ценообразования и складского учёта. "
        "Приватные эндпоинты требуют `Authorization: Bearer <JWT>` и, для "
        "магазинных данных, заголовок `X-Store-ID`."
    ),
    version="0.3.0",
    openapi_tags=TAGS_METADATA,
)

# add_middleware: последний добавленный — внешний; RequestId должен оборачивать всё.
app.add_middleware(TenantMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if exc.status_code >= 500:
        logger.error(
            "api error",
            extra={"request_id": request_id, "error_code": exc.error_code},
        )
    return error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.info("validation error", extra={"request_id": request_id})
    return error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="Ошибка валидации запроса",
        details={"errors": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if exc.status_code >= 500:
        logger.error("http exception", extra={"request_id": request_id})
    detail = exc.detail
    if isinstance(detail, dict) and {"error_code", "message"} <= set(detail):
        return JSONResponse(
            status_code=exc.status_code, content=detail, headers=exc.headers
        )
    return error_response(
        status_code=exc.status_code,
        error_code=STATUS_ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
        message=str(detail) if detail else "Ошибка запроса",
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("unhandled error", extra={"request_id": request_id})
    return error_response(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="Внутренняя ошибка сервера",
    )


for router in (
    auth.router,
    stores.router,
    products.router,
    inventory.router,
    wms.router,
    barcodes.router,
    recommendations.router,
    analytics.router,
):
    app.include_router(router)


@app.get(
    "/health",
    tags=["Сервис"],
    summary="Проверка живости сервиса",
    responses={200: {"description": "Сервис доступен"}},
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
