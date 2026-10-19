"""Unit-тесты инструментов агента (SDD §3.2.2–3.2.3; §7.1 — без LLM).

Проверяют на тестовой БД (фикстура shop):
- get_stock_level: сумма партий, сортировка по expiry, min_days_to_expiry;
- get_sales_trend: сумма/среднее/тренд по двум половинам окна;
- check_external_factors: данные есть/нет, битая дата;
- calculate_reorder_amount / calculate_margin_impact: числа приходят из
  calculations.py, не от LLM;
- call_tool: whitelist (Tool Registry) и валидация аргументов.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from backend.app.db.session import SessionLocal
from backend.app.models import ExternalFactor, Inventory, SalesHistory
from backend.app.models import StoreProduct as StoreProductModel
from backend.app.services.ai import tools
from backend.app.services.calculations import FORECAST_DAYS

TODAY = datetime.now(UTC).date()


async def _seed_store_data(store_id: int, product_id: int) -> None:
    """Остатки, продажи, цена и внешний фактор для пары (магазин, товар)."""
    async with SessionLocal() as session:
        session.add_all(
            [
                Inventory(
                    product_id=product_id,
                    store_id=store_id,
                    quantity=50,
                    batch_date=TODAY - timedelta(days=5),
                    expiry_date=TODAY + timedelta(days=10),
                ),
                Inventory(
                    product_id=product_id,
                    store_id=store_id,
                    quantity=20,
                    batch_date=TODAY - timedelta(days=3),
                    expiry_date=TODAY + timedelta(days=2),
                ),
                StoreProductModel(
                    product_id=product_id,
                    store_id=store_id,
                    current_price=Decimal("89.99"),
                    is_active=True,
                ),
                ExternalFactor(
                    store_id=store_id,
                    date=TODAY,
                    weather_condition="sunny",
                    is_holiday=False,
                    demand_multiplier=Decimal("1.20"),
                ),
            ]
        )
        # 10 продаж x 3 шт за последние FORECAST_DAYS дней -> средний спрос 1.0
        for offset in range(0, FORECAST_DAYS, 3):
            session.add(
                SalesHistory(
                    product_id=product_id,
                    store_id=store_id,
                    quantity_sold=3,
                    sale_price=Decimal("89.99"),
                    sale_date=datetime.now(UTC) - timedelta(days=offset),
                )
            )
        await session.commit()


async def test_get_stock_level(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    await _seed_store_data(store_id, product_id)
    async with SessionLocal() as session:
        result = await tools.get_stock_level(
            tools.GetStockLevelArgs(product_id=product_id, store_id=store_id),
            session,
        )
    assert result["total_quantity"] == 70
    assert len(result["batches"]) == 2
    # партии отсортированы по expiry: ближайшая первая
    assert result["batches"][0]["days_to_expiry"] == 2
    assert result["min_days_to_expiry"] == 2


async def test_get_sales_trend(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    await _seed_store_data(store_id, product_id)
    async with SessionLocal() as session:
        result = await tools.get_sales_trend(
            tools.GetSalesTrendArgs(
                product_id=product_id, store_id=store_id, days=FORECAST_DAYS
            ),
            session,
        )
    assert result["total_sold"] == 30  # 10 x 3
    assert result["avg_daily_sales"] == 1.0
    assert result["trend"] in ("flat", "rising", "falling")


async def test_get_sales_trend_no_data(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    async with SessionLocal() as session:
        result = await tools.get_sales_trend(
            tools.GetSalesTrendArgs(product_id=product_id, store_id=store_id),
            session,
        )
    assert result["total_sold"] == 0
    assert result["trend"] == "no_data"


async def test_check_external_factors(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    await _seed_store_data(store_id, product_id)
    async with SessionLocal() as session:
        result = await tools.check_external_factors(
            tools.CheckExternalFactorsArgs(store_id=store_id, date=TODAY.isoformat()),
            session,
        )
    assert result["available"] is True
    assert result["weather_condition"] == "sunny"
    assert result["demand_multiplier"] == 1.2


async def test_check_external_factors_missing_date(shop) -> None:
    store_id = shop["store_ids"][0]
    async with SessionLocal() as session:
        result = await tools.check_external_factors(
            tools.CheckExternalFactorsArgs(
                store_id=store_id, date=(TODAY + timedelta(days=40)).isoformat()
            ),
            session,
        )
    assert result["available"] is False
    assert result["demand_multiplier"] == 1.0


async def test_check_external_factors_bad_date(shop) -> None:
    async with SessionLocal() as session:
        result = await tools.check_external_factors(
            tools.CheckExternalFactorsArgs(store_id=1, date="вчера"),
            session,
        )
    assert result["error_code"] == "BAD_DATE"


async def test_calculate_reorder_amount(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    await _seed_store_data(store_id, product_id)
    async with SessionLocal() as session:
        result = await tools.calculate_reorder_amount(
            tools.CalculateReorderAmountArgs(product_id=product_id, store_id=store_id),
            session,
        )
    # средний спрос 1.0 x 3 дня + min_stock 10 - остаток 70 -> 0
    assert result["reorder_amount"] == 0
    assert result["current_stock"] == 70
    assert result["min_stock"] == 10
    assert result["avg_daily_sales"] == 1.0


async def test_calculate_margin_impact(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    await _seed_store_data(store_id, product_id)
    async with SessionLocal() as session:
        result = await tools.calculate_margin_impact(
            tools.CalculateMarginImpactArgs(
                product_id=product_id, store_id=store_id, new_price=Decimal("99.99")
            ),
            session,
        )
    # forecast = 1.0 x 1.2 x 30 = 36; (99.99-65) * 36 - (89.99-65) * 36 = 360
    assert result["expected_impact"] == 360.0
    assert result["current_price"] == 89.99
    assert result["base_cost"] == 65.0


async def test_calculate_margin_impact_product_not_found(shop) -> None:
    async with SessionLocal() as session:
        result = await tools.calculate_margin_impact(
            tools.CalculateMarginImpactArgs(
                product_id=999, store_id=1, new_price=Decimal(100)
            ),
            session,
        )
    assert result["error_code"] == "PRODUCT_NOT_FOUND"


async def test_call_tool_whitelist(shop) -> None:
    async with SessionLocal() as session:
        result = await tools.call_tool("rm_rf", {"path": "/"}, session)
    assert result["error_code"] == "TOOL_NOT_ALLOWED"


async def test_call_tool_bad_arguments(shop) -> None:
    async with SessionLocal() as session:
        result = await tools.call_tool(
            "get_stock_level", {"product_id": "abc"}, session
        )
    assert result["error_code"] == "TOOL_BAD_ARGUMENTS"


async def test_call_tool_timeout(shop, monkeypatch) -> None:
    from pydantic import BaseModel

    class _AnyArgs(BaseModel):
        dummy: int | None = None

    async def slow(args, db):
        import asyncio

        await asyncio.sleep(tools.TOOL_TIMEOUT_SECONDS + 0.1)
        return {}

    monkeypatch.setitem(tools.REGISTRY, "slow_tool", None)
    spec = tools.ToolSpec("slow_tool", "тест", _AnyArgs, slow)
    tools.REGISTRY["slow_tool"] = spec
    try:
        async with SessionLocal() as session:
            result = await tools.call_tool("slow_tool", {}, session)
        assert result["error_code"] == "TOOL_TIMEOUT"
    finally:
        del tools.REGISTRY["slow_tool"]


def test_openai_tools_schema_whitelist_only() -> None:
    schema = tools.openai_tools_schema()
    names = {item["function"]["name"] for item in schema}
    assert names == {
        "get_stock_level",
        "get_sales_trend",
        "check_external_factors",
        "calculate_reorder_amount",
        "calculate_margin_impact",
    }
    assert all(item["type"] == "function" for item in schema)
