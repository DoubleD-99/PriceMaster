"""Integration-тесты контракта рекомендаций и алертов (SDD §6.4–6.5)."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models import (
    Inventory,
    PriceHistory,
    PriceRecommendation,
    SalesHistory,
    StoreProduct,
)
from backend.app.schemas.ai import AIRecommendationResponse
from backend.app.services import calculations


async def _add_store_product(product_id: int, store_id: int, price: str) -> None:
    async with SessionLocal() as session:
        session.add(
            StoreProduct(
                product_id=product_id,
                store_id=store_id,
                current_price=Decimal(price),
                is_active=True,
            )
        )
        await session.commit()


async def _add_recommendation(
    *,
    product_id: int,
    store_id: int,
    action_type: str = "price_change",
    value: str = "90.00",
    status: str = "pending",
) -> int:
    async with SessionLocal() as session:
        row = PriceRecommendation(
            product_id=product_id,
            store_id=store_id,
            action_type=action_type,
            recommended_value=Decimal(value),
            reasoning="Тестовая рекомендация",
            confidence=0.8,
            status=status,
            expected_impact=Decimal("10.00"),
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


def _headers(store_id: int) -> dict[str, str]:
    return {"X-Store-ID": str(store_id)}


async def test_alerts_include_zero_stock_active_product(auth_client, shop) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    await _add_store_product(product_id, store_id, "100.00")

    response = await auth_client.get("/inventory/alerts", headers=_headers(store_id))

    assert response.status_code == 200
    body = response.json()
    assert {"product_id": product_id, "quantity": 0, "min_stock": 10} in body[
        "low_stock"
    ]


async def test_alerts_include_expiring_batch(auth_client, shop) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    today = datetime.now(UTC).date()
    async with SessionLocal() as session:
        session.add(
            Inventory(
                product_id=product_id,
                store_id=store_id,
                quantity=3,
                batch_date=today - timedelta(days=5),
                expiry_date=today + timedelta(days=2),
            )
        )
        await session.commit()

    response = await auth_client.get("/inventory/alerts", headers=_headers(store_id))

    assert response.status_code == 200
    expiring = response.json()["expiring_soon"]
    assert len(expiring) == 1
    assert expiring[0]["product_id"] == product_id
    assert expiring[0]["days_left"] == 2


async def test_accept_price_change_updates_price_and_history(auth_client, shop) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    await _add_store_product(product_id, store_id, "100.00")
    recommendation_id = await _add_recommendation(
        product_id=product_id, store_id=store_id
    )

    response = await auth_client.post(
        f"/recommendations/{recommendation_id}/accept",
        headers=_headers(store_id),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"

    async with SessionLocal() as session:
        price = await session.scalar(
            select(StoreProduct.current_price).where(
                StoreProduct.product_id == product_id,
                StoreProduct.store_id == store_id,
            )
        )
        history = await session.scalar(
            select(PriceHistory).where(
                PriceHistory.recommendation_id == recommendation_id
            )
        )
    assert price == Decimal("90.00")
    assert history is not None


async def test_accept_is_idempotency_guard(auth_client, shop) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    recommendation_id = await _add_recommendation(
        product_id=product_id,
        store_id=store_id,
        action_type="reorder",
    )

    first = await auth_client.post(
        f"/recommendations/{recommendation_id}/accept",
        headers=_headers(store_id),
    )
    second = await auth_client.post(
        f"/recommendations/{recommendation_id}/accept",
        headers=_headers(store_id),
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error_code"] == "RECOMMENDATION_ALREADY_PROCESSED"


async def test_reject_does_not_change_price(auth_client, shop) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    await _add_store_product(product_id, store_id, "100.00")
    recommendation_id = await _add_recommendation(
        product_id=product_id, store_id=store_id
    )

    response = await auth_client.post(
        f"/recommendations/{recommendation_id}/reject",
        headers=_headers(store_id),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    async with SessionLocal() as session:
        price = await session.scalar(
            select(StoreProduct.current_price).where(
                StoreProduct.product_id == product_id,
                StoreProduct.store_id == store_id,
            )
        )
    assert price == Decimal("100.00")


async def test_list_recommendations_filters_by_status(auth_client, shop) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    await _add_recommendation(product_id=product_id, store_id=store_id)
    await _add_recommendation(
        product_id=product_id,
        store_id=store_id,
        status="accepted",
    )

    all_rows = await auth_client.get("/recommendations", headers=_headers(store_id))
    pending = await auth_client.get(
        "/recommendations",
        params={"status": "pending"},
        headers=_headers(store_id),
    )

    assert all_rows.status_code == 200
    assert len(all_rows.json()) == 2
    assert [row["status"] for row in pending.json()] == ["pending"]


async def test_generate_uses_pipeline_and_mock_agent(
    auth_client, shop, monkeypatch
) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    await _add_store_product(product_id, store_id, "100.00")

    async def fake_analyze(
        product_id: int,
        store_id: int,
        db,
        client=None,
    ) -> AIRecommendationResponse:
        return AIRecommendationResponse(
            action_type="price_change",
            recommended_value=95.0,
            reasoning="Тестовый ответ агента",
            confidence=0.9,
            expected_impact=12.5,
            tool_calls_used=["get_stock_level"],
        )

    monkeypatch.setattr("backend.app.services.ai.agent.analyze_product", fake_analyze)

    response = await auth_client.post(
        "/recommendations/generate",
        json={"limit": 5},
        headers=_headers(store_id),
    )

    assert response.status_code == 200, response.text
    rows = response.json()
    assert any(row["product_id"] == product_id for row in rows)
    assert all(row["status"] == "pending" for row in rows)


async def test_generate_api_to_agent_with_mock_llm(
    auth_client, shop, mock_llm, monkeypatch
) -> None:
    store_id = shop["store_ids"][0]
    product_id = shop["product_ids"][0]
    await _add_store_product(product_id, store_id, "100.00")
    async with SessionLocal() as session:
        session.add(
            SalesHistory(
                product_id=product_id,
                store_id=store_id,
                quantity_sold=60,
                sale_price=Decimal("100.00"),
                sale_date=datetime.now(UTC),
            )
        )
        await session.commit()

    expected_impact = calculations.margin_impact(
        base_cost=Decimal("65.00"),
        current_price=Decimal("100.00"),
        new_price=Decimal("90.00"),
        avg_daily_sales=Decimal(2),
    )
    mock_llm.queue_tool_call(
        "calculate_margin_impact",
        {"product_id": product_id, "store_id": store_id, "new_price": "90.00"},
    )
    mock_llm.queue_final(
        {
            "action_type": "price_change",
            "recommended_value": 90.0,
            "reasoning": "Скидка ускорит продажи",
            "confidence": 0.8,
            "expected_impact": float(expected_impact),
            "tool_calls_used": [],
        }
    )
    monkeypatch.setattr("backend.app.services.ai.agent.make_client", lambda: mock_llm)

    response = await auth_client.post(
        "/recommendations/generate",
        json={"product_id": product_id},
        headers=_headers(store_id),
    )

    assert response.status_code == 200, response.text
    row = response.json()[0]
    assert row["product_id"] == product_id
    assert Decimal(str(row["expected_impact"])) == expected_impact

    tool_messages = [
        message
        for message in mock_llm.calls[1]["messages"]
        if message.get("role") == "tool"
    ]
    tool_results = [json.loads(message["content"]) for message in tool_messages]
    assert any(
        result["expected_impact"] == float(expected_impact) for result in tool_results
    )
