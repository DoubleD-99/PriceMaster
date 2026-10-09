"""Пакет бизнес-сервисов backend (SDD, раздел 3.1; не зависит от HTTP).

- wms.py             — приёмка/списание/партии/алёрты (Приложение A, раздел 6);
- analytics.py       — агрегации продаж для /analytics/sales;
- calculations.py    — маржинальность, цены, reorder — ЕДИНСТВЕННЫЙ источник
                       чисел для агента (docs/agents.md, правило 2);
- external_factors.py- синтетика внешних факторов (погода/праздник/demand_multiplier);
- synthetic_data.py  — генерация товаров, остатков и продаж для seed;
- ai/                — LLM-агент: agent.py, tools.py, prompts.py.

Сервис calculations переиспользуется агентом (services/ai/tools.py) — числа к LLM
приходят только из этих функций.
"""
