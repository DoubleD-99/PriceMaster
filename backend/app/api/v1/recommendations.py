"""AI и рекомендации — контракт SDD §6.4.

- POST /recommendations/generate — анализ одного товара или кандидатов
  pipeline; результат сохраняется со статусом `pending`;
- GET /recommendations — список рекомендаций магазина (фильтр `status`,
  сортировка по `created_at` DESC);
- POST /recommendations/{id}/accept — принять: `price_change` обновляет
  `store_products` и пишет `price_history`; `reorder`/`write_off` меняют
  только статус (D-08);
- POST /recommendations/{id}/reject — отклонить без изменения цены (D-09).

Требуется JWT + X-Store-ID; 404 — неизвестный id, 409 — повторная обработка.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.deps import DbDep, StoreDep
from backend.app.schemas import (
    ErrorResponse,
    RecommendationGenerateRequest,
    RecommendationOut,
    RecommendationStatus,
)
from backend.app.services import recommendations as service

router = APIRouter(tags=["recommendations"])

ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _recommendation_error(exc: service.RecommendationError) -> JSONResponse:
    """Ответ в едином формате ошибок SDD §6.2."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@router.post(
    "/recommendations/generate",
    response_model=list[RecommendationOut],
    responses=ERROR_RESPONSES,
)
async def generate_recommendations(
    body: RecommendationGenerateRequest,
    db: DbDep,
    store_id: StoreDep,
) -> list[RecommendationOut] | JSONResponse:
    """Запустить анализ и сохранить новые рекомендации."""
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
    return [RecommendationOut.model_validate(row) for row in rows]


@router.get(
    "/recommendations",
    response_model=list[RecommendationOut],
    responses=ERROR_RESPONSES,
)
async def list_recommendations(
    db: DbDep,
    store_id: StoreDep,
    status: RecommendationStatus | None = None,
) -> list[RecommendationOut]:
    """Рекомендации магазина, новые сверху."""
    rows = await service.list_recommendations(db, store_id=store_id, status=status)
    return [RecommendationOut.model_validate(row) for row in rows]


@router.post(
    "/recommendations/{recommendation_id}/accept",
    response_model=RecommendationOut,
    responses=ERROR_RESPONSES,
)
async def accept_recommendation(
    recommendation_id: int,
    db: DbDep,
    store_id: StoreDep,
) -> RecommendationOut | JSONResponse:
    """Принять рекомендацию (human-in-the-loop)."""
    try:
        row = await service.accept_recommendation(
            db, store_id=store_id, recommendation_id=recommendation_id
        )
    except service.RecommendationError as exc:
        return _recommendation_error(exc)
    await db.commit()
    return RecommendationOut.model_validate(row)


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=RecommendationOut,
    responses=ERROR_RESPONSES,
)
async def reject_recommendation(
    recommendation_id: int,
    db: DbDep,
    store_id: StoreDep,
) -> RecommendationOut | JSONResponse:
    """Отклонить рекомендацию без изменения цены."""
    try:
        row = await service.reject_recommendation(
            db, store_id=store_id, recommendation_id=recommendation_id
        )
    except service.RecommendationError as exc:
        return _recommendation_error(exc)
    await db.commit()
    return RecommendationOut.model_validate(row)
