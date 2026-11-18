"""Магазины - GET /stores."""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, UserDep
from backend.app.models import Store
from backend.app.schemas import ErrorResponse, StoreOut

router = APIRouter(tags=["Магазины"])


@router.get(
    "/stores",
    response_model=list[StoreOut],
    summary="Список доступных магазинов",
    responses={401: {"model": ErrorResponse}},
)
async def list_stores(db: DbDep, user: UserDep) -> list[StoreOut]:
    rows = await db.scalars(
        select(Store).where(Store.id.in_(user.store_ids)).order_by(Store.id)
    )
    return [StoreOut.model_validate(row) for row in rows]
