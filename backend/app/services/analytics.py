"""Аналитическая агрегация - SDD, раздел 3.1, модуль services/."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import SalesHistory

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value: Decimal | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT)


def _day_bounds(day_from: date | None, day_to: date | None):
    start = datetime.combine(day_from, time.min, tzinfo=UTC) if day_from else None
    end = (
        datetime.combine(day_to + timedelta(days=1), time.min, tzinfo=UTC)
        if day_to
        else None
    )
    return start, end


async def get_sales_analytics(
    db: AsyncSession,
    *,
    store_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: int | None = None,
) -> dict:
    filters = [SalesHistory.store_id == store_id]
    start, end = _day_bounds(date_from, date_to)
    if start is not None:
        filters.append(SalesHistory.sale_date >= start)
    if end is not None:
        filters.append(SalesHistory.sale_date < end)
    if product_id is not None:
        filters.append(SalesHistory.product_id == product_id)

    revenue_expr = func.coalesce(
        func.sum(SalesHistory.quantity_sold * SalesHistory.sale_price), 0
    )
    quantity_expr = func.coalesce(func.sum(SalesHistory.quantity_sold), 0)
    count_expr = func.count(SalesHistory.id)

    summary_row = (
        await db.execute(
            select(
                revenue_expr.label("revenue"),
                quantity_expr.label("quantity"),
                count_expr.label("sales_count"),
            ).where(*filters)
        )
    ).one()
    total_revenue = _money(summary_row.revenue)
    total_quantity = int(summary_row.quantity or 0)
    sales_count = int(summary_row.sales_count or 0)
    average_check = _money(total_revenue / sales_count) if sales_count else ZERO

    day_expr = func.date(SalesHistory.sale_date).label("day")
    by_day_rows = (
        await db.execute(
            select(
                day_expr,
                revenue_expr.label("revenue"),
                quantity_expr.label("quantity"),
                count_expr.label("sales_count"),
            )
            .where(*filters)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    by_day = []
    for row in by_day_rows:
        day_revenue = _money(row.revenue)
        day_count = int(row.sales_count or 0)
        day_value = row.day
        if isinstance(day_value, str):
            day_value = date.fromisoformat(day_value)
        elif isinstance(day_value, datetime):
            day_value = day_value.date()
        by_day.append(
            {
                "date": day_value,
                "revenue": day_revenue,
                "quantity": int(row.quantity or 0),
                "sales_count": day_count,
                "average_check": _money(day_revenue / day_count) if day_count else ZERO,
            }
        )

    by_product_rows = (
        await db.execute(
            select(
                SalesHistory.product_id.label("product_id"),
                revenue_expr.label("revenue"),
                quantity_expr.label("quantity"),
                count_expr.label("sales_count"),
            )
            .where(*filters)
            .group_by(SalesHistory.product_id)
            .order_by(revenue_expr.desc(), SalesHistory.product_id)
        )
    ).all()
    by_product = []
    for row in by_product_rows:
        product_revenue = _money(row.revenue)
        product_count = int(row.sales_count or 0)
        by_product.append(
            {
                "product_id": int(row.product_id),
                "revenue": product_revenue,
                "quantity": int(row.quantity or 0),
                "sales_count": product_count,
                "average_check": (
                    _money(product_revenue / product_count) if product_count else ZERO
                ),
            }
        )

    return {
        "summary": {
            "total_revenue": total_revenue,
            "total_quantity": total_quantity,
            "sales_count": sales_count,
            "average_check": average_check,
        },
        "by_day": by_day,
        "by_product": by_product,
    }
