"""Остатки - GET /inventory, GET /inventory/alerts."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from backend.app.api.deps import DbDep, StoreDep
from backend.app.models import Inventory
from backend.app.schemas import ErrorResponse, InventoryAlertsOut, InventoryOut
from backend.app.services import wms

router = APIRouter(tags=["Остатки"])


@router.get(
    "/inventory/alerts",
    response_model=InventoryAlertsOut,
    summary="Алерты по остаткам",
    description="Истекающие партии и товары с остатком ниже min_stock.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_inventory_alerts(
    db: DbDep,
    store_id: StoreDep,
) -> InventoryAlertsOut:
    return InventoryAlertsOut.model_validate(await wms.alerts(db, store_id=store_id))


@router.get(
    "/inventory",
    response_model=list[InventoryOut],
    summary="Партии остатков магазина",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def list_inventory(
    db: DbDep,
    store_id: StoreDep,
    product_id: int | None = Query(default=None, description="Фильтр по товару"),
) -> list[InventoryOut]:
    stmt = select(Inventory).where(Inventory.store_id == store_id)
    if product_id is not None:
        stmt = stmt.where(Inventory.product_id == product_id)
    stmt = stmt.order_by(
        Inventory.product_id, Inventory.expiry_date, Inventory.batch_date
    )
    rows = await db.scalars(stmt)
    return [InventoryOut.model_validate(row) for row in rows]
