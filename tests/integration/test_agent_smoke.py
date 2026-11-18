"""Smoke-тест агента на синтетических данных (TODO итерации 2).

Проверяет полный backend-pipeline: синтетические справочники/остатки/продажи
→ POST /recommendations/generate → tool calling (mock LLM) → сохранённая
pending-рекомендация с валидными полями.
"""

from datetime import UTC, datetime

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models import PriceRecommendation, Product, Store
from backend.app.services import external_factors, synthetic_data


async def test_agent_smoke_on_synthetic_data(auth_client, shop, mock_llm, monkeypatch):
    store_id = shop["store_ids"][0]
    today = datetime.now(UTC).date()

    async with SessionLocal() as session:
        stores = list(
            (
                await session.scalars(
                    select(Store).where(Store.id.in_(shop["store_ids"]))
                )
            ).all()
        )
        products = list(
            (
                await session.scalars(
                    select(Product).where(Product.id.in_(shop["product_ids"]))
                )
            ).all()
        )
        store_products = synthetic_data.make_store_products(stores, products)
        session.add_all(store_products)
        await session.flush()
        prices = {
            (sp.store_id, sp.product_id): sp.current_price for sp in store_products
        }
        session.add_all(synthetic_data.make_inventory(stores, products, today=today))
        session.add_all(
            synthetic_data.make_sales(stores, products, prices, today=today)
        )
        session.add_all(external_factors.generate([s.id for s in stores], today=today))
        await session.commit()
        product = products[0]

    mock_llm.queue_tool_call(
        "get_stock_level",
        {"product_id": product.id, "store_id": store_id},
    )
    mock_llm.queue_final(
        {
            "action_type": "reorder",
            "recommended_value": 12.0,
            "reasoning": "Синтетические данные показывают низкий остаток, нужна закупка.",
            "confidence": 0.88,
            "expected_impact": 0.0,
            "tool_calls_used": [],
        }
    )
    monkeypatch.setattr("backend.app.services.ai.agent.make_client", lambda: mock_llm)

    response = await auth_client.post(
        "/recommendations/generate",
        json={"product_id": product.id},
        headers={"X-Store-ID": str(store_id)},
    )

    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "pending"
    assert row["product_id"] == product.id
    assert row["store_id"] == store_id
    assert row["action_type"] == "reorder"
    assert row["reasoning"]
    assert 0.0 <= row["confidence"] <= 1.0

    async with SessionLocal() as session:
        saved = list(
            (
                await session.scalars(
                    select(PriceRecommendation).where(
                        PriceRecommendation.store_id == store_id,
                        PriceRecommendation.product_id == product.id,
                    )
                )
            ).all()
        )
    assert len(saved) == 1
    assert saved[0].status == "pending"

    tool_messages = [
        message
        for message in mock_llm.calls[1]["messages"]
        if message.get("role") == "tool"
    ]
    assert tool_messages, "ожидался tool-result в контексте LLM"
