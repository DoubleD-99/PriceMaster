"""Скрипт наполнения БД синтетическими данными (seed).

Запуск:  python -m backend.seed_db   (из корня репозитория)

Что делает (через services/synthetic_data.py и external_factors.py):
1. Создаёт схему таблиц (Base.metadata.create_all);
2. Очищает таблицы данных (идемпотентность: повторный запуск
   пересоздаёт набор, а не удваивает его);
3. Заполняет 3 магазина, каталог, цены, остатки партиями, продажи
   за 6 месяцев с сезонностью, днями недели и demand_multiplier;
4. Генерирует external_factors на исторический период + будущие 2 недели;
5. Создаёт историю цен (price_history) и пустую таблицу рекомендаций.

Данные детерминированы (seed=42) — воспроизводимы между запусками.
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text

from backend.app.db.session import Base, SessionLocal, engine
from backend.app.models import (
    Barcode,
    ExternalFactor,
    Inventory,
    PriceHistory,
    PriceRecommendation,
    Product,
    SalesHistory,
    Store,
    StoreProduct,
)
from backend.app.services import external_factors, synthetic_data

# Дочерние таблицы — перед родительскими (FK restrict).
CLEANUP_ORDER = [
    PriceHistory,
    PriceRecommendation,
    Inventory,
    SalesHistory,
    ExternalFactor,
    StoreProduct,
    Barcode,
    Product,
    Store,
]

COUNTED = [
    Store,
    Product,
    Barcode,
    StoreProduct,
    Inventory,
    SalesHistory,
    PriceHistory,
    ExternalFactor,
    PriceRecommendation,
]


async def seed() -> dict[str, int]:
    """Пересоздать синтетические данные; вернуть количество строк по таблицам."""
    today = datetime.now(UTC).date()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        for model in CLEANUP_ORDER:
            await db.execute(delete(model))
            # Сброс serial-последовательностей: повторный seed даёт те же id
            # (важно для токенов, выданных до пересоздания данных).
            if db.get_bind().dialect.name == "postgresql":
                await db.execute(
                    text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), 1, false)"),
                    {"tbl": model.__tablename__},
                )

        stores = synthetic_data.make_stores()
        db.add_all(stores)
        await db.flush()

        products = synthetic_data.make_products()
        db.add_all(products)
        await db.flush()

        db.add_all(synthetic_data.make_barcodes(products))
        await db.flush()

        store_products = synthetic_data.make_store_products(stores, products)
        db.add_all(store_products)
        await db.flush()
        prices = {
            (sp.store_id, sp.product_id): sp.current_price for sp in store_products
        }

        db.add_all(synthetic_data.make_inventory(stores, products, today=today))
        await db.flush()

        db.add_all(synthetic_data.make_sales(stores, products, prices, today=today))
        await db.flush()

        db.add_all(
            synthetic_data.make_price_history(stores, products, prices, today=today)
        )
        await db.flush()

        db.add_all(external_factors.generate([s.id for s in stores], today=today))
        await db.commit()

        counts: dict[str, int] = {}
        for model in COUNTED:
            total = (
                await db.execute(select(func.count()).select_from(model))
            ).scalar_one()
            counts[model.__tablename__] = int(total)
        return counts


def main() -> None:
    counts = asyncio.run(seed())
    width = max(len(name) for name in counts)
    print("Seed выполнен:")
    for name, total in counts.items():
        print(f"  {name.ljust(width)}  {total}")


if __name__ == "__main__":
    main()
