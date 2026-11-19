"""AI и рекомендации - контракт SDD §6.4."""

from decimal import Decimal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import DbDep, StoreDep
from backend.app.api.errors import error_response
from backend.app.models import Inventory, PriceRecommendation, StoreProduct
from backend.app.schemas import (
    ErrorResponse,
    RecommendationGenerateRequest,
    RecommendationOut,
    RecommendationStatus,
)
from backend.app.services import recommendations as service

router = APIRouter(tags=["Рекомендации"])


async def _with_current_values(
    db: AsyncSession,
    store_id: int,
    rows: list[PriceRecommendation],
) -> list[RecommendationOut]:
    product_ids = {row.product_id for row in rows}
    if not product_ids:
        return []
    price_result = await db.execute(
        select(StoreProduct.product_id, StoreProduct.current_price).where(
            StoreProduct.store_id == store_id,
            StoreProduct.product_id.in_(product_ids),
            StoreProduct.is_active.is_(True),
        )
    )
    prices = {product_id: Decimal(price) for product_id, price in price_result.all()}
    stock_result = await db.execute(
        select(Inventory.product_id, func.sum(Inventory.quantity))
        .where(
            Inventory.store_id == store_id,
            Inventory.product_id.in_(product_ids),
        )
        .group_by(Inventory.product_id)
    )
    stocks = {product_id: int(total or 0) for product_id, total in stock_result.all()}
    return [
        RecommendationOut.model_validate(row).model_copy(
            update={
                "current_price": prices.get(row.product_id),
                "current_stock": stocks.get(row.product_id, 0),
            }
        )
        for row in rows
    ]


ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _recommendation_error(exc: service.RecommendationError) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


@router.post(
    "/recommendations/generate",
    response_model=list[RecommendationOut],
    summary="Сгенерировать рекомендации",
    description="Выбирает кандидатов, запускает AI-пайплайн и сохраняет pending-рекомендации.",
    responses=ERROR_RESPONSES,
)
async def generate_recommendations(
    body: RecommendationGenerateRequest,
    db: DbDep,
    store_id: StoreDep,
) -> list[RecommendationOut] | JSONResponse:
    try:
        rows = await service.generate_recommendations(
            db,
            store_id=store_id,
            product_id=body.product_id,
            limit=body.limit,
        )
    except service.RecommendationError as exc:
        return _recommendation_error(exc)
    await db.commit()
    return await _with_current_values(db, store_id, rows)


@router.get(
    "/recommendations",
    response_model=list[RecommendationOut],
    summary="Список рекомендаций",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_recommendations(
    db: DbDep,
    store_id: StoreDep,
    status: RecommendationStatus | None = Query(  # noqa: B008
        default=None, description="Фильтр по статусу"
    ),
) -> list[RecommendationOut]:
    rows = await service.list_recommendations(db, store_id=store_id, status=status)
    return await _with_current_values(db, store_id, rows)


@router.post(
    "/recommendations/{recommendation_id}/accept",
    response_model=RecommendationOut,
    summary="Принять рекомендацию",
    responses=ERROR_RESPONSES,
)
async def accept_recommendation(
    recommendation_id: int,
    db: DbDep,
    store_id: StoreDep,
) -> RecommendationOut | JSONResponse:
    try:
        row = await service.accept_recommendation(
            db, store_id=store_id, recommendation_id=recommendation_id
        )
    except service.RecommendationError as exc:
        return _recommendation_error(exc)
    await db.commit()
    return (await _with_current_values(db, store_id, [row]))[0]


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=RecommendationOut,
    summary="Отклонить рекомендацию",
    responses=ERROR_RESPONSES,
)
async def reject_recommendation(
    recommendation_id: int,
    db: DbDep,
    store_id: StoreDep,
) -> RecommendationOut | JSONResponse:
    try:
        row = await service.reject_recommendation(
            db, store_id=store_id, recommendation_id=recommendation_id
        )
    except service.RecommendationError as exc:
        return _recommendation_error(exc)
    await db.commit()
    return (await _with_current_values(db, store_id, [row]))[0]
