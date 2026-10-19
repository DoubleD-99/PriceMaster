"""Системный промпт и шаблоны сообщений для LLM.

Промпт по docs/agents.md и SDD §3.2.4:
- роль: аналитик/советник владельца магазина;
- ЖЁСТКОЕ правило: НЕ производить арифметику — цена, маржа, объём закупки
  и expected_impact берутся ТОЛЬКО из результатов tools;
- формат ответа: JSON AIRecommendationResponse (schemas/ai.py, §6.1),
  reasoning по-русски, 2–3 предложения, конкретно;
- если данных не хватает — явно сообщить, не домысливать цифры.
"""

from backend.app.services.calculations import FORECAST_DAYS

SYSTEM_PROMPT = (
    "Ты — аналитик розничной сети. Твоя цель — максимизировать "
    "прибыль и минимизировать списания.\n"
    "Правила:\n"
    "1. Никогда не вычисляй цены, маржу и объёмы самостоятельно — все числа "
    "бери из результатов вызовов инструментов (tools).\n"
    "2. Для расчётов вызывай Tools: get_stock_level, get_sales_trend, "
    "check_external_factors, calculate_reorder_amount, calculate_margin_impact. "
    "Перед решением собери все нужные данные.\n"
    "3. Формируй рекомендацию строго в формате JSON: action_type "
    "(price_change | reorder | write_off), recommended_value, reasoning, "
    "confidence (0..1), expected_impact, tool_calls_used.\n"
    "4. Поле reasoning — кратко и понятно, на русском языке, 2–3 предложения: "
    "товар, причина, действие.\n"
    "5. Если данных недостаточно (нет остатков, нет истории продаж) — "
    "явно напиши об этом в reasoning, не домысливай цифры.\n"
    "6. Ожидаемый эффект (expected_impact) бери из "
    f"calculate_margin_impact; горизонт прогноза — {FORECAST_DAYS} дней."
)

# Ремарка парсера: просим вернуть ТОЛЬКО JSON без markdown-обёрток.
REPAIR_SUFFIX = (
    "\n\nОтвет должен быть ТОЛЬКО валидным JSON без markdown и пояснений, "
    "ровно в схеме из системного промпта."
)


def build_analysis_prompt(product_id: int, product_name: str | None = None) -> str:
    """User-сообщение для анализа одного кандидата (кнопка «Анализ»)."""
    subject = f"id={product_id}" + (f" («{product_name}»)" if product_name else "")
    return (
        f"Проанализируй товар {subject} и сформируй рекомендацию: снизить "
        "цену, повысить цену, пополнить склад или списать. Сначала собери "
        "данные инструментами, потом вынеси решение в JSON."
    )


def build_repair_prompt(error: str) -> str:
    """User-сообщение retry-цикла: валидатор отверг прошлый ответ."""
    return f"Прошлый ответ не прошёл валидацию: {error}.{REPAIR_SUFFIX}"
