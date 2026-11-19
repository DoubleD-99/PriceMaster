"""Расчётные функции: маржинальность, прогноз продаж, объём закупки (reorder).

ЕДИНСТВЕННЫЙ источник чисел для агента (docs/agents.md, правило 2). LLM их не
вычисляет — только вызывает через services/ai/tools.py и вставляет готовые
значения в обоснование.

Формулы (SDD §6.3, §3.2.3):
- expected_impact = profit_new - profit_current, где profit учитывает списание
  партий, не успевших продаться до истечения срока; без данных об остатках
  используется упрощённая формула (new_price - base_cost) * forecast_sales -
  (current_price - base_cost) * forecast_sales;
- reorder = ceil(средний дневной спрос x срок поставки + min_stock - остаток).

Функции чистые: принимают все данные аргументами, БД не трогают (чтение —
в tools.py). Вся арифметика — Decimal, деньги округляются до 0.1 ROUND_HALF_UP.

Каждая функция покрыта unit-тестами tests/unit/test_calculations.py.
"""

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

# Горизонт прогноза продаж, дней (ожидаемый эффект считаем на месяц).
FORECAST_DAYS = 30
# Срок поставки заказа, дней (в products поля нет — фиксированная константа).
LEAD_TIME_DAYS = 3
PRICE_QUANT = Decimal("0.1")


def round_money(value: Decimal | float | str) -> Decimal:
    """Деньги и цены — один знак после запятой, ROUND_HALF_UP."""
    return _d(value).quantize(PRICE_QUANT, rounding=ROUND_HALF_UP)


def _d(value: Decimal | float | str) -> Decimal:
    """Нормализация входа в Decimal (float → через str, без погрешности)."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def margin_pct(base_cost: Decimal | float, price: Decimal | float) -> Decimal:
    """Процент маржи: (price - base_cost) / price * 100. При price=0 — 0."""
    price_d = _d(price)
    if price_d == 0:
        return Decimal("0.00")
    return round_money((_d(price) - _d(base_cost)) / price_d * 100)


def discount_price(
    current_price: Decimal | float, discount_pct: Decimal | float
) -> Decimal:
    """Цена со скидкой: current_price * (1 - discount_pct / 100)."""
    return round_money(_d(current_price) * (Decimal(1) - _d(discount_pct) / 100))


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
    total_stock: Decimal | float | None = None,
    at_risk_quantity: Decimal | float | None = None,
) -> Decimal:
    """Ожидаемый эффект смены цены (expected_impact, SDD §6.3).

    Если известны остатки, сравнивается полная прибыль: продажи минус списание
    партий, которые истекают в горизонте прогноза и не успевают продаться.
    Скидка увеличивает объём продаж в квадрате обратного отношения цен
    (эластичность спроса = 2), за счёт чего часть партии спасается от списания.
    Без данных об остатках используется простая разница маржи на одном и том
    же прогнозе продаж.
    """
    sales = forecast_sales(avg_daily_sales, demand_multiplier, days)
    cost_d = _d(base_cost)
    current_d = _d(current_price)
    new_d = _d(new_price)
    if (
        total_stock is None
        or at_risk_quantity is None
        or _d(total_stock) <= 0
        or current_d <= 0
        or new_d <= 0
    ):
        return round_money((new_d - cost_d) * sales - (current_d - cost_d) * sales)

    stock_d = _d(total_stock)
    risk_d = min(_d(at_risk_quantity), stock_d)
    sold_current = min(sales, stock_d)
    price_ratio = current_d / new_d
    sold_new = min(sales * price_ratio * price_ratio, stock_d)
    write_off_current = max(Decimal(0), risk_d - min(sold_current, risk_d))
    write_off_new = max(Decimal(0), risk_d - min(sold_new, risk_d))
    profit_current = (current_d - cost_d) * sold_current - write_off_current * cost_d
    profit_new = (new_d - cost_d) * sold_new - write_off_new * cost_d
    return round_money(profit_new - profit_current)


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
