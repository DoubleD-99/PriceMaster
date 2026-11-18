"""Системный промпт и шаблоны сообщений для LLM.

Промпт по docs/agents.md и SDD §3.2.4:
- роль: аналитик розничной сети;
- строгие правила: не придумывать арифметику - цены, остатки, объем заказа
  и expected_impact берутся только из результатов tools;
- формат ответа: JSON AIRecommendationResponse (schemas/ai.py, §6.1),
  reasoning по-русски, 2-3 предложения, конкретно;
- если данных не хватает - явно указать, не домысливать цифры.
"""

from backend.app.services.calculations import FORECAST_DAYS

SYSTEM_PROMPT = (
    "Ты - аналитик розничной сети. Цель - максимизировать прибыль и минимизировать списания.\n"
    "Правила:\n"
    "1. Не придумывай числа: цены, остатки, продажи, объем заказа и expected_impact "
    "бери только из результатов инструментов (tools).\n"
    "2. Перед решением собери факты инструментами: get_stock_level, get_sales_trend, "
    "check_external_factors, calculate_reorder_amount, calculate_margin_impact. "
    "Вызывай только нужные tools, используя параметры из задачи.\n"
    "3. Для tools передавай product_id и store_id из задачи. Для check_external_factors "
    "используй дату из задачи (сегодня) в формате YYYY-MM-DD.\n"
    "4. Верни строго один JSON-объект без markdown: action_type "
    "(price_change | reorder | write_off), recommended_value, reasoning, "
    "confidence (0..1), expected_impact. Поле tool_calls_used заполняется системой.\n"
    "5. reasoning - кратко и конкретно, по-русски, 2-3 предложения: товар, причина, действие.\n"
    "6. expected_impact бери из результата calculate_margin_impact; прогнозный горизонт - "
    f"{FORECAST_DAYS} дней.\n"
    "7. Если данных недостаточно (нет остатков, активной цены или истории продаж) - "
    "явно укажи это в reasoning и не выдумывай цифры."
)

REPAIR_SUFFIX = (
    "\n\nОтвет должен быть только валидным JSON без markdown и пояснений, "
    "строго по схеме из системного промпта."
)


def build_analysis_prompt(
    product_id: int,
    store_id: int,
    today: str,
    product_name: str | None = None,
) -> str:
    """User-сообщение для анализа одного товара."""
    subject = f"товар id={product_id}" + (
        f" («{product_name}»)" if product_name else ""
    )
    return (
        f"Проанализируй {subject} для магазина store_id={store_id}. "
        f"Сегодня: {today} (YYYY-MM-DD).\n"
        "Собери данные инструментами (get_stock_level, get_sales_trend, "
        "check_external_factors, calculate_reorder_amount, calculate_margin_impact), "
        "передавая эти product_id/store_id и дату today для check_external_factors. "
        "Затем верни рекомендацию в JSON: изменить цену, заказать товар или списать."
    )


def build_repair_prompt(error: str) -> str:
    """User-сообщение retry-цикла: прошлый ответ не прошёл валидацию."""
    return f"Прошлый ответ не прошёл валидацию: {error}.{REPAIR_SUFFIX}"
