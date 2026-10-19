"""Складская бизнес-логика (WMS) — SDD, раздел 3.1, модуль services/.

- receiving  — приёмка: партия (batch_date, expiry_date) + обновление
               остатков; повторная приёмка той же партии суммирует количество;
- write_off  — списание: выбор партий по FIFO (раньше всех списывается
               партия с наименьшим expiry_date, затем batch_date — раздел 3.3),
               в рамках одной транзакции; нехватка остатка — WmsError
               (WMS_INSUFFICIENT_STOCK, формат раздела 6.2);
- alerts     — алёрты: срок годности < 3 дней, quantity < min_stock
               (Приложение A, раздел 6).

Вызывается роутером api/v1/wms; не зависит от HTTP.
Числовые расчёты — только здесь или в calculations.py (docs/agents.md, правило 2).
"""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Inventory, Product

EXPIRY_ALERT_DAYS = 3


class WmsError(Exception):
    """Бизнес-ошибка WMS; роутер мапит её в ответ формата SDD 6.2."""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code


async def receiving(
    db: AsyncSession,
    *,
    store_id: int,
    product_id: int,
    quantity: int,
    batch_date: date,
    expiry_date: date,
) -> tuple[Inventory, int]:
    """Приёмка товара: новая партия или суммирование с существующей.

    Возвращает (строка inventory, добавленное количество).
    """
    if quantity <= 0:
        raise WmsError(
            "WMS_INVALID_QUANTITY", "Количество приёмки должно быть больше 0"
        )
    if expiry_date < batch_date:
        raise WmsError(
            "WMS_INVALID_EXPIRY",
            "Срок годности не может быть раньше даты партии",
            {"batch_date": str(batch_date), "expiry_date": str(expiry_date)},
        )

    product = await db.get(Product, product_id)
    if product is None:
        raise WmsError(
            "PRODUCT_NOT_FOUND", f"Товар id={product_id} не найден", status_code=404
        )

    batch = await db.scalar(
        select(Inventory).where(
            Inventory.store_id == store_id,
            Inventory.product_id == product_id,
            Inventory.batch_date == batch_date,
            Inventory.expiry_date == expiry_date,
        )
    )
    if batch is None:
        batch = Inventory(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            batch_date=batch_date,
            expiry_date=expiry_date,
        )
        db.add(batch)
    else:
        batch.quantity += quantity

    await db.flush()
    await db.refresh(batch)
    return batch, quantity


async def write_off(
    db: AsyncSession,
    *,
    store_id: int,
    product_id: int,
    quantity: int,
    reason: str,
) -> list[dict]:
    """Списание по FIFO: партии с наименьшим expiry_date списываются первыми.

    Возвращает [{batch_id, expiry_date, quantity}, ...] — сколько снято
    с каждой партии. Недостаточный остаток -> WmsError (транзакция цела).
    """
    if quantity <= 0:
        raise WmsError(
            "WMS_INVALID_QUANTITY", "Количество списания должно быть больше 0"
        )
    if not reason.strip():
        raise WmsError("WMS_INVALID_REASON", "Причина списания обязательна")

    rows = (
        await db.scalars(
            select(Inventory)
            .where(
                Inventory.store_id == store_id,
                Inventory.product_id == product_id,
                Inventory.quantity > 0,
            )
            .order_by(Inventory.expiry_date, Inventory.batch_date, Inventory.id)
            .with_for_update()
        )
    ).all()

    available = sum(row.quantity for row in rows)
    if available < quantity:
        raise WmsError(
            "WMS_INSUFFICIENT_STOCK",
            "Недостаточно товара для списания",
            {"requested": quantity, "available": available, "store_id": store_id},
        )

    remaining = quantity
    written_off: list[dict] = []
    for row in rows:
        if remaining == 0:
            break
        take = min(remaining, row.quantity)
        row.quantity -= take
        remaining -= take
        written_off.append(
            {"batch_id": row.id, "expiry_date": row.expiry_date, "quantity": take}
        )

    await db.flush()
    return written_off


async def alerts(
    db: AsyncSession,
    *,
    store_id: int,
    today: date | None = None,
) -> dict[list[dict]]:
    """Алёрты магазина: истекающие партии и остатки ниже min_stock."""
    today = today or datetime.now(UTC).date()

    expiring = [
        {"product_id": r[0], "batch_id": r[1], "expiry_date": r[2], "days_left": r[3]}
        for r in (
            await db.execute(
                select(
                    Inventory.product_id,
                    Inventory.id,
                    Inventory.expiry_date,
                ).where(
                    Inventory.store_id == store_id,
                    Inventory.quantity > 0,
                )
            )
        )
        if 0 <= (r[2] - today).days <= EXPIRY_ALERT_DAYS
    ]

    stocks = await db.execute(
        select(Inventory.product_id, Inventory.quantity).where(
            Inventory.store_id == store_id
        )
    )
    stock_by_product: dict[int, int] = {}
    for product_id, quantity in stocks:
        stock_by_product[product_id] = stock_by_product.get(product_id, 0) + quantity

    thresholds = {
        p.id: p.min_stock
        for p in (
            await db.scalars(select(Product).where(Product.id.in_(stock_by_product)))
        ).all()
    }
    low_stock = [
        {"product_id": pid, "quantity": qty, "min_stock": thresholds.get(pid, 0)}
        for pid, qty in sorted(stock_by_product.items())
        if qty < thresholds.get(pid, 0)
    ]

    return {"expiring_soon": expiring, "low_stock": low_stock}
