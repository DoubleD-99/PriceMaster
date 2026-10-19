"""Штрихкоды — GET /barcodes/{code} (SDD, Приложение A, разделы 5–6).

Поиск товара по штрихкоду (таблица `barcodes`): данные товара для
приёмки/списания в PWA. Сканирование камеры в браузере — html5-qrcode
(раздел A.10, экран Scanner).

Требуется JWT; 404, если код не найден.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.app.api.deps import DbDep, UserDep
from backend.app.models import Barcode, Product
from backend.app.schemas import ProductOut

router = APIRouter(tags=["barcodes"])


@router.get("/barcodes/{code}", response_model=ProductOut)
async def get_product_by_barcode(code: str, db: DbDep, user: UserDep) -> ProductOut:
    """Товар по штрихкоду; 404, если код не зарегистрирован."""
    row = await db.scalar(
        select(Product)
        .join(Barcode, Barcode.product_id == Product.id)
        .where(Barcode.code == code)
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Штрихкод {code} не найден")
    return ProductOut.model_validate(row)
