"""Unit-тесты расчётных функций (SDD §6.3, §3.2.3; docs/agents.md, правило 2).

Числа для рекомендаций считаются ТОЛЬКО здесь — тесты фиксируют формулы:
- expected_impact = (new_price - base_cost) * forecast - current_profit;
- reorder = ceil(спрос x срок поставки + min_stock - остаток).
"""

from decimal import Decimal

from backend.app.services import calculations as calc


def test_margin_pct() -> None:
    assert calc.margin_pct(60, 100) == Decimal("40.00")
    assert calc.margin_pct(Decimal("65.50"), Decimal("100.00")) == Decimal("34.50")
    assert calc.margin_pct(60, 0) == Decimal("0.00")  # деление на ноль обезврежено


def test_discount_price() -> None:
    assert calc.discount_price(200, 10) == Decimal("180.00")
    assert calc.discount_price(Decimal("99.99"), Decimal("15.5")) == Decimal("84.49")


def test_forecast_sales() -> None:
    # 2 шт/день x 1.5 x 30 дней
    assert calc.forecast_sales(2, 1.5) == Decimal(90)
    assert calc.forecast_sales(0, 2, days=7) == Decimal(0)


def test_margin_impact_formula() -> None:
    # forecast = 1.0 x 1.2 x 30 = 36; impact = (99.99-65) * 36 - (89.99-65) * 36
    impact = calc.margin_impact(
        base_cost=65,
        current_price=89.99,
        new_price=99.99,
        avg_daily_sales=1,
        demand_multiplier=1.2,
    )
    assert impact == Decimal("360.00")


def test_margin_impact_negative_when_price_drops() -> None:
    impact = calc.margin_impact(
        base_cost=65,
        current_price=89.99,
        new_price=69.99,
        avg_daily_sales=1,
    )
    assert impact < 0


def test_margin_impact_no_sales_no_effect() -> None:
    impact = calc.margin_impact(65, 89.99, 99.99, avg_daily_sales=0)
    assert impact == Decimal("0.00")


def test_reorder_amount_basic() -> None:
    # спрос 2/день x 3 дня + min 10 - остаток 4 = 12
    assert calc.reorder_amount(2, current_stock=4, min_stock=10) == 12


def test_reorder_amount_zero_when_stock_enough() -> None:
    assert calc.reorder_amount(1, current_stock=100, min_stock=10) == 0


def test_reorder_amount_rounds_up() -> None:
    # 1.5 x 3 = 4.5 -> ceil 5
    assert calc.reorder_amount(1.5, current_stock=0) == 5


def test_reorder_amount_fractional_sales() -> None:
    # 0.33 x 30 дней истории = средний спрос; reorder на 3 дня поставки
    amount = calc.reorder_amount(Decimal("0.33"), current_stock=0)
    assert amount == 1  # ceil(0.99)
