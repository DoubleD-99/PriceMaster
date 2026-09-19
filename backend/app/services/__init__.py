"""Пакет бизнес-сервисов backend.

Содержит:
- calculations.py    — расчёты маржинальности и объёма закупки (reorder);
- external_factors.py— синтетическая генерация погоды/праздников/demand_multiplier;
- synthetic_data.py  — генерация товаров, остатков и продаж с сезонностью.
Сервис calculations переиспользуется агентом (ai_agent/tools.py) — числа к LLM
поступают только из этих функций.
"""