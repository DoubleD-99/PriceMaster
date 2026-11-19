"""Штрихкоды - GET /barcodes/{code}."""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, UserDep
from backend.app.api.errors import ApiError
from backend.app.models import Barcode, Product
from backend.app.schemas import ErrorResponse, ProductOut

router = APIRouter(tags=["Штрихкоды"])


@router.get(
    "/barcodes/{code}",
    response_model=ProductOut,
    summary="Поиск товара по штрихкоду",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Штрихкод не найден"},
    },
)
async def get_product_by_barcode(code: str, db: DbDep, user: UserDep) -> ProductOut:
    row = await db.scalar(
        select(Product)
        .join(Barcode, Barcode.product_id == Product.id)
        .where(Barcode.code == code)
    )
    if row is None:
        raise ApiError(
            "BARCODE_NOT_FOUND",
            f"Штрихкод {code} не найден",
            status_code=404,
            details={"code": code},
        )
    return ProductOut.model_validate(row)
