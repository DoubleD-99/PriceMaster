"""Аналитика - GET /analytics/sales."""

from datetime import date

from fastapi import APIRouter, Query

from backend.app.api.deps import DbDep, StoreDep
from backend.app.api.errors import ApiError
from backend.app.schemas import ErrorResponse, SalesAnalyticsOut
from backend.app.services import analytics as service

router = APIRouter(tags=["Аналитика"])


@router.get(
    "/analytics/sales",
    response_model=SalesAnalyticsOut,
    summary="Агрегация продаж магазина",
    description=(
        "Возвращает суммарные показатели, продажи по дням и по товарам "
        "для выбранного магазина (X-Store-ID)."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Некорректные параметры запроса"},
        401: {"model": ErrorResponse, "description": "Требуется аутентификация"},
        403: {"model": ErrorResponse, "description": "Нет доступа к магазину"},
    },
)
async def get_sales_analytics(
    db: DbDep,
    store_id: StoreDep,
    date_from: date | None = Query(  # noqa: B008
        default=None, description="Начало периода (YYYY-MM-DD, включительно)"
    ),
    date_to: date | None = Query(  # noqa: B008
        default=None, description="Конец периода (YYYY-MM-DD, включительно)"
    ),
    product_id: int | None = Query(default=None, description="Фильтр по товару"),
) -> SalesAnalyticsOut:
    if date_from and date_to and date_from > date_to:
        raise ApiError(
            "INVALID_DATE_RANGE",
            "date_from не может быть позже date_to",
            status_code=400,
        )
    result = await service.get_sales_analytics(
        db,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
    )
    return SalesAnalyticsOut.model_validate(result)
