"""Расчётные функции: маржинальность, прогноз продаж, объём закупки (reorder).

ЕДИНСТВЕННЫЙ источник чисел для агента (docs/agents.md, правило 2). LLM их не
вычисляет — только вызывает через services/ai/tools.py и вставляет готовые
значения в обоснование.

Формулы (SDD §6.3, §3.2.3):
- expected_impact = (new_price - base_cost) * forecast_sales - current_profit,
  где forecast_sales = средний дневной спрос x demand_multiplier x горизонт,
  current_profit  = (current_price - base_cost) * forecast_sales;
- reorder = ceil(средний дневной спрос x срок поставки + min_stock - остаток).

Функции чистые: принимают все данные аргументами, БД не трогают (чтение —
в tools.py). Вся арифметика — Decimal, округление 0.01 ROUND_HALF_UP.

Каждая функция покрыта unit-тестами tests/unit/test_calculations.py.
"""

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

# Горизонт прогноза продаж, дней (ожидаемый эффект считаем на месяц).
FORECAST_DAYS = 30
# Срок поставки заказа, дней (в products поля нет — фиксированная константа).
LEAD_TIME_DAYS = 3


def _d(value: Decimal | float | str) -> Decimal:
    """Нормализация входа в Decimal (float → через str, без погрешности)."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    """Округление до копеек."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def margin_pct(base_cost: Decimal | float, price: Decimal | float) -> Decimal:
    """Процент маржи: (price - base_cost) / price * 100. При price=0 — 0."""
    price_d = _d(price)
    if price_d == 0:
        return Decimal("0.00")
    return _money((_d(price) - _d(base_cost)) / price_d * 100)


def discount_price(
    current_price: Decimal | float, discount_pct: Decimal | float
) -> Decimal:
    """Цена со скидкой: current_price * (1 - discount_pct / 100)."""
    return _money(_d(current_price) * (Decimal(1) - _d(discount_pct) / 100))


def forecast_sales(
    avg_daily_sales: Decimal | float,
    demand_multiplier: Decimal | float = 1,
    days: int = FORECAST_DAYS,
) -> Decimal:
    """Прогноз объёма продаж за horizon дней: спрос x множитель x дни."""
    return _d(avg_daily_sales) * _d(demand_multiplier) * days


def margin_impact(
    base_cost: Decimal | float,
    current_price: Decimal | float,
    new_price: Decimal | float,
    avg_daily_sales: Decimal | float,
    demand_multiplier: Decimal | float = 1,
    days: int = FORECAST_DAYS,
) -> Decimal:
    """Ожидаемый эффект смены цены (expected_impact, SDD §6.3).

    (new_price - base_cost) * forecast_sales - current_profit, где
    current_profit = (current_price - base_cost) * тот же forecast_sales.
    Отрицательное значение — новый ценой прибыль упадёт.
    """
    sales = forecast_sales(avg_daily_sales, demand_multiplier, days)
    new_profit = (_d(new_price) - _d(base_cost)) * sales
    current_profit = (_d(current_price) - _d(base_cost)) * sales
    return _money(new_profit - current_profit)


def reorder_amount(
    avg_daily_sales: Decimal | float,
    current_stock: Decimal | float,
    min_stock: Decimal | float = 0,
    lead_time_days: int = LEAD_TIME_DAYS,
) -> int:
    """Объём закупки для пополнения склада (SDD §3.2.3).

    ceil(средний дневной спрос x срок поставки + min_stock - остаток);
    если остатка хватает — 0. Кратность упаковки в схеме БД нет,
    нормируется до целых штук (вверх).
    """
    target = _d(avg_daily_sales) * lead_time_days + _d(min_stock)
    gap = target - _d(current_stock)
    if gap <= 0:
        return 0
    return int(gap.to_integral_value(rounding=ROUND_CEILING))
