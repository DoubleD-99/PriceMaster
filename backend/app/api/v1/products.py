"""Товары - GET /products."""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, StoreDep, UserDep
from backend.app.api.errors import ApiError
from backend.app.models import PriceHistory, Product, StoreProduct
from backend.app.schemas import (
    ErrorResponse,
    PriceHistoryOut,
    ProductOut,
    ProductPriceOut,
)

router = APIRouter(tags=["Товары"])


@router.get(
    "/products",
    response_model=list[ProductOut],
    summary="Каталог товаров",
    responses={401: {"model": ErrorResponse}},
)
async def list_products(db: DbDep, user: UserDep) -> list[ProductOut]:
    rows = await db.scalars(select(Product).order_by(Product.name))
    return [ProductOut.model_validate(row) for row in rows]


@router.get(
    "/products/{product_id}/price",
    response_model=ProductPriceOut,
    summary="Текущая цена товара в магазине",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Активная цена не найдена"},
    },
)
async def get_product_price(
    product_id: int,
    db: DbDep,
    store_id: StoreDep,
) -> ProductPriceOut:
    row = await db.scalar(
        select(StoreProduct).where(
            StoreProduct.product_id == product_id,
            StoreProduct.store_id == store_id,
            StoreProduct.is_active.is_(True),
        )
    )
    if row is None:
        raise ApiError(
            "PRICE_NOT_FOUND",
            f"Для товара id={product_id} в магазине id={store_id} нет активной цены",
            status_code=404,
            details={"product_id": product_id, "store_id": store_id},
        )
    return ProductPriceOut.model_validate(row)


@router.get(
    "/products/{product_id}/price-history",
    response_model=list[PriceHistoryOut],
    summary="История цен товара в магазине",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def get_price_history(
    product_id: int,
    db: DbDep,
    store_id: StoreDep,
) -> list[PriceHistoryOut]:
    rows = await db.scalars(
        select(PriceHistory)
        .where(
            PriceHistory.product_id == product_id,
            PriceHistory.store_id == store_id,
        )
        .order_by(PriceHistory.changed_at.desc(), PriceHistory.id.desc())
    )
    return [PriceHistoryOut.model_validate(row) for row in rows]
