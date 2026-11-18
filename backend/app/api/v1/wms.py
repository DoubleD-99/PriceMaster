"""Складские операции (WMS)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.deps import DbDep, StoreDep
from backend.app.api.errors import error_response
from backend.app.schemas import (
    ErrorResponse,
    InventoryOut,
    ReceivingCreate,
    ReceivingResult,
    WriteOffCreate,
    WriteOffResult,
)
from backend.app.services import wms

router = APIRouter(tags=["WMS"])


def _wms_error(exc: wms.WmsError) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


@router.post(
    "/wms/receiving",
    status_code=201,
    response_model=ReceivingResult,
    summary="Приёмка партии",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def receiving(
    body: ReceivingCreate,
    db: DbDep,
    store_id: StoreDep,
) -> ReceivingResult | JSONResponse:
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


@router.post(
    "/wms/write-off",
    response_model=WriteOffResult,
    summary="Списание по FIFO",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def write_off(
    body: WriteOffCreate,
    db: DbDep,
    store_id: StoreDep,
) -> WriteOffResult | JSONResponse:
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
