"""Товары — GET /products (SDD, Приложение A, раздел 5).

Список товаров общего каталога (`products`). Секции 6/7 не фильтруют
каталог по магазину: общий каталог общий для сети, цены и остатки
привязаны к магазину отдельно (store_products, inventory).

Требуется JWT; ответ 401 без токена.
"""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, UserDep
from backend.app.models import Product
from backend.app.schemas import ProductOut

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
async def list_products(db: DbDep, user: UserDep) -> list[ProductOut]:
    """Каталог товаров (сортировка по названию)."""
    rows = await db.scalars(select(Product).order_by(Product.name))
    return [ProductOut.model_validate(row) for row in rows]
