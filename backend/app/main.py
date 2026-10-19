"""Входная точка FastAPI-приложения (SDD, раздел 3.1).

Здесь создаётся экземпляр `app`, подключаются TenantMiddleware (JWT +
изоляция по X-Store-ID, раздел 3.4) и роутеры api/v1 (Приложение A,
раздел 5): auth, stores, products, inventory, wms, barcodes,
recommendations, analytics — пути монтируются без общего префикса,
ровно как в спецификации.

Запуск (из корня репозитория):
    python -m uvicorn backend.app.main:app --reload

Документация API: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from backend.app.api.middleware import TenantMiddleware
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

app = FastAPI(
    title="Price Master API",
    description="Агентное динамическое ценообразование и упрощённый WMS (SDD).",
    version="0.1.0",
)

app.add_middleware(TenantMiddleware)

# Пути — один в один по Приложению A, раздел 5 (без общего префикса).
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


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    """Проверка живости сервиса (docker-compose healthcheck)."""
    return {"status": "ok"}
