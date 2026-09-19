"""Расчётные функции: маржинальность и объём закупки (reorder).

ЕДИНСТВЕННЫЙ источник чисел для агента (см. agents.md, правило 2). LLM их
не вычисляет — только вызывает через ai_agent/tools.py.

Планируемые функции:
- calculate_margin(base_cost, current_price) -> Decimal  — процент маржи;
- calculate_discount_price(current_price, discount_pct)  — цена со скидкой;
- calculate_reorder_amount(product_id, ...)              — объём закупки
  (учитывает средний спрос из sales_history, текущий остаток и срок доставки).

Каждая покрывается unit-тестами в tests/unit/test_calculations.py.
"""
