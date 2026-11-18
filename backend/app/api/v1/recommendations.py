"""AI и рекомендации - контракт SDD §6.4."""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.app.api.deps import DbDep, StoreDep
from backend.app.api.errors import error_response
from backend.app.schemas import (
    ErrorResponse,
    RecommendationGenerateRequest,
    RecommendationOut,
    RecommendationStatus,
)
from backend.app.services import recommendations as service

router = APIRouter(tags=["Рекомендации"])

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
    return [RecommendationOut.model_validate(row) for row in rows]


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
    return [RecommendationOut.model_validate(row) for row in rows]


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
    return RecommendationOut.model_validate(row)


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
    return RecommendationOut.model_validate(row)
