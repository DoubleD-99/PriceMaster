"""Товары - GET /products."""

from fastapi import APIRouter
from sqlalchemy import select

from backend.app.api.deps import DbDep, UserDep
from backend.app.models import Product
from backend.app.schemas import ErrorResponse, ProductOut

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
