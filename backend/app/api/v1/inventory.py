"""Остатки — GET /inventory (SDD, Приложение A, раздел 5).

Текущие остатки выбранного магазина (X-Store-ID) с разбивкой по партиям
(`batch_date`, `expiry_date`) — Приложение A, раздел 6.

Требуется JWT + X-Store-ID; 400 без/при неверном X-Store-ID.
"""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, StoreDep
from backend.app.models import Inventory
from backend.app.schemas import InventoryAlertsOut, InventoryOut
from backend.app.services import wms

router = APIRouter(tags=["inventory"])


@router.get("/inventory/alerts", response_model=InventoryAlertsOut)
async def list_inventory_alerts(
    db: DbDep,
    store_id: StoreDep,
) -> InventoryAlertsOut:
    """Истекающие партии и остатки ниже `min_stock` (D-10)."""
    return InventoryAlertsOut.model_validate(await wms.alerts(db, store_id=store_id))


@router.get("/inventory", response_model=list[InventoryOut])
async def list_inventory(
    db: DbDep,
    store_id: StoreDep,
    product_id: int | None = None,
) -> list[InventoryOut]:
    """Партии остатков магазина; опциональный фильтр ?product_id=."""
    stmt = select(Inventory).where(Inventory.store_id == store_id)
    if product_id is not None:
        stmt = stmt.where(Inventory.product_id == product_id)
    stmt = stmt.order_by(
        Inventory.product_id, Inventory.expiry_date, Inventory.batch_date
    )
    rows = await db.scalars(stmt)
    return [InventoryOut.model_validate(row) for row in rows]
