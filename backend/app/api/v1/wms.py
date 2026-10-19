"""Складские операции (WMS) — SDD, Приложение A, разделы 5 и 6.

- POST /wms/receiving — приёмка; Body { product_id, quantity, batch_date,
  expiry_date }: запись партии + обновление остатков;
- POST /wms/write-off — списание; Body { product_id, quantity, reason }:
  фиксация убытка (порча/истечение срока), списание по партиям FIFO
  (срок годности раньше списывается раньше) — раздел 3.3.

Бизнес-логика — в backend.app.services.wms (не зависит от HTTP).
Ошибки — формат SDD, раздел 6.2: { error_code, message, details }.
Требуется JWT + X-Store-ID; 400 при нехватке остатков/невалидных данных.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.deps import DbDep, StoreDep
from backend.app.schemas import (
    InventoryOut,
    ReceivingCreate,
    ReceivingResult,
    WriteOffCreate,
    WriteOffResult,
)
from backend.app.services import wms

router = APIRouter(tags=["wms"])


def _wms_error(exc: wms.WmsError) -> JSONResponse:
    """Ответ об ошибке в формате SDD, раздел 6.2."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@router.post("/wms/receiving", status_code=201, response_model=ReceivingResult)
async def receiving(
    body: ReceivingCreate,
    db: DbDep,
    store_id: StoreDep,
) -> ReceivingResult | JSONResponse:
    """Приёмка товара в выбранный магазин (партия batch_date/expiry_date)."""
    try:
        batch, added = await wms.receiving(
            db,
            store_id=store_id,
            product_id=body.product_id,
            quantity=body.quantity,
            batch_date=body.batch_date,
            expiry_date=body.expiry_date,
        )
    except wms.WmsError as exc:
        return _wms_error(exc)
    await db.commit()
    return ReceivingResult(
        batch=InventoryOut.model_validate(batch), quantity_added=added
    )


@router.post("/wms/write-off", response_model=WriteOffResult)
async def write_off(
    body: WriteOffCreate,
    db: DbDep,
    store_id: StoreDep,
) -> WriteOffResult | JSONResponse:
    """Списание товара по FIFO (партии с наименьшим expiry_date первыми)."""
    try:
        batches = await wms.write_off(
            db,
            store_id=store_id,
            product_id=body.product_id,
            quantity=body.quantity,
            reason=body.reason,
        )
    except wms.WmsError as exc:
        return _wms_error(exc)
    await db.commit()
    return WriteOffResult(
        product_id=body.product_id,
        store_id=store_id,
        quantity=body.quantity,
        reason=body.reason,
        batches=batches,
    )
