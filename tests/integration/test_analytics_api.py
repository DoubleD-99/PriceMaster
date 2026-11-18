"""Integration tests for sales analytics endpoint (iteration 3)."""

from datetime import UTC, datetime
from decimal import Decimal

from backend.app.db.session import SessionLocal
from backend.app.models import SalesHistory


async def _sale(
    *, store_id: int, product_id: int, quantity: int, price: str, when: datetime
):
    async with SessionLocal() as session:
        session.add(
            SalesHistory(
                store_id=store_id,
                product_id=product_id,
                quantity_sold=quantity,
                sale_price=Decimal(price),
                sale_date=when,
            )
        )
        await session.commit()


async def test_sales_analytics_aggregates_by_day_and_product(auth_client, shop):
    store_id = shop["store_ids"][0]
    p1, p2 = shop["product_ids"][0], shop["product_ids"][1]
    await _sale(
        store_id=store_id,
        product_id=p1,
        quantity=2,
        price="100.00",
        when=datetime(2026, 11, 1, 10, tzinfo=UTC),
    )
    await _sale(
        store_id=store_id,
        product_id=p1,
        quantity=1,
        price="100.00",
        when=datetime(2026, 11, 1, 12, tzinfo=UTC),
    )
    await _sale(
        store_id=store_id,
        product_id=p2,
        quantity=3,
        price="50.00",
        when=datetime(2026, 11, 2, 9, tzinfo=UTC),
    )

    response = await auth_client.get(
        "/analytics/sales", headers={"X-Store-ID": str(store_id)}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["total_quantity"] == 6
    assert Decimal(str(body["summary"]["total_revenue"])) == Decimal("450.00")
    assert body["summary"]["sales_count"] == 3
    assert len(body["by_day"]) == 2
    assert len(body["by_product"]) == 2
    assert {row["product_id"] for row in body["by_product"]} == {p1, p2}


async def test_sales_analytics_filters_and_validates_range(auth_client, shop):
    store_id = shop["store_ids"][0]
    p1 = shop["product_ids"][0]
    await _sale(
        store_id=store_id,
        product_id=p1,
        quantity=1,
        price="10.00",
        when=datetime(2026, 11, 5, 10, tzinfo=UTC),
    )

    filtered = await auth_client.get(
        "/analytics/sales",
        params={"date_from": "2026-11-01", "date_to": "2026-11-03"},
        headers={"X-Store-ID": str(store_id)},
    )
    assert filtered.status_code == 200
    assert filtered.json()["summary"]["sales_count"] == 0

    bad = await auth_client.get(
        "/analytics/sales",
        params={"date_from": "2026-11-10", "date_to": "2026-11-01"},
        headers={"X-Store-ID": str(store_id)},
    )
    assert bad.status_code == 400
    assert bad.json()["error_code"] == "INVALID_DATE_RANGE"
