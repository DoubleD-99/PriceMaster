"""Магазины — GET /stores (SDD, Приложение A, раздел 5).

Список доступных магазинов (таблица `stores`, 2–3 штуки — Приложение A,
раздел 7). Используется PWA для выпадающего выбора магазина в шапке;
выбранный магазин передаётся далее в заголовке X-Store-ID.

Требуется JWT; ответ 401 без токена.
"""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, UserDep
from backend.app.models import Store
from backend.app.schemas import StoreOut

router = APIRouter(tags=["stores"])


@router.get("/stores", response_model=list[StoreOut])
async def list_stores(db: DbDep, user: UserDep) -> list[StoreOut]:
    """Магазины, доступные текущему токену (store_ids из JWT)."""
    rows = await db.scalars(
        select(Store).where(Store.id.in_(user.store_ids)).order_by(Store.id)
    )
    return [StoreOut.model_validate(row) for row in rows]
