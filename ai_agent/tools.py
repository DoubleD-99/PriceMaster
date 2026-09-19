"""Инструменты (Tools) агента.

Единственный способ получить числа для LLM: агент вызывает эти функции и
вставляет готовые значения в контекст. Самостоятельно LLM не вычисляет
ничего (агенты.md, правило 2).

Список по ТЗ (раздел 3):
- get_stock_level(product_id)            — текущие остатки + дни до истечения;
- get_sales_trend(product_id, days)      — средняя/тренд продаж за N дней;
- check_external_factors(date)           — погода, праздник, demand_multiplier;
- calculate_reorder_amount(product_id)   — объём закупки на пополнение склада
  (делегируется backend.app.services.calculations).

Данные читаются из БД напрямую (СеssionLocal) либо через REST-эндпоинты backend.
Каждая функция возвращает готовые числа для prompts.py.
"""
