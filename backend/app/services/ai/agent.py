"""Оркестрация AI-агента: цикл Tool Calling (SDD §3.2.1).

Поток (Итерации 2 будет подключён к POST /recommendations/generate):
1. system (prompts.py) + user о кандидате → chat.completions с tools=
   (whitelist из tools.REGISTRY, §3.2.5);
2. LLM возвращает tool_calls → выполняем их через tools.call_tool
   (read-only сессия БД, timeout 10 c) → результаты возвращаем модели;
3. повторяем до финального текстового ответа (не более MAX_TOOL_ITERATIONS);
4. парсер извлекает JSON и валидирует AIRecommendationResponse (§6.1);
   при ValidationError / битом JSON — retry с ремаркой (до 3 попыток, §9);
5. tool_calls_used перезаписывается реальным списком вызванных tools
   (поле для аудита — не доверяем памяти LLM).

Изменение цены из агента НЕВОЗМОЖНО: tools только читают, запись цены —
исключительно POST /recommendations/{id}/accept (§3.2.5).

Клиент LLM инжектируется (параметр client) — unit-тесты гоняют цикл с
моком, без реального API (§7.1).
"""

import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.schemas.ai import AIRecommendationResponse
from backend.app.services.ai import prompts, tools

# Максимум последовательных вызовов tools в одном цикле (защита от зацикливания).
MAX_TOOL_ITERATIONS = 5
# Попытки вытянуть валидный JSON из ответа LLM (риск «битого JSON», §9).
MAX_REPAIR_ATTEMPTS = 3


def make_client() -> AsyncOpenAI | None:
    """Клиент OpenAI-совместимого API (Qwen); None — если не сконфигурирован."""
    if not settings.LLM_API_URL or not settings.LLM_API_KEY:
        return None
    return AsyncOpenAI(
        base_url=settings.LLM_API_URL or None, api_key=settings.LLM_API_KEY
    )


def parse_recommendation(text: str) -> AIRecommendationResponse:
    """JSON из ответа LLM (терпим к ```json-обёртке) → Pydantic (§6.1).

    Битый JSON → json.JSONDecodeError, невалидные поля → ValidationError —
    обе ошибки ловятся в retry-цикле analyze_product.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    data: Any = json.loads(cleaned)
    return AIRecommendationResponse.model_validate(data)


async def _execute_tool_calls(tool_calls: list[Any], db: Any) -> list[dict]:
    """Выполнить tool_calls из ответа LLM; аргументы-мусор — ошибка в результат."""
    results = []
    for call in tool_calls:
        name = call.function.name
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = None
        if args is None:
            result = {
                "error_code": "TOOL_BAD_ARGUMENTS",
                "message": "Аргументы инструмента не являются валидным JSON",
            }
        else:
            result = await tools.call_tool(name, args, db)
        results.append({"tool_call_id": call.id, "name": name, "result": result})
    return results


async def _parse_with_repair(
    client: AsyncOpenAI,
    messages: list[dict],
    content: str,
    db: Any,
) -> AIRecommendationResponse:
    """Retry-цикл парсинга: битый ответ → ремарка → повторный запрос LLM."""
    text = content
    last_error: Exception | None = None
    for _ in range(MAX_REPAIR_ATTEMPTS):
        try:
            return parse_recommendation(text)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": text})
            messages.append(
                {
                    "role": "user",
                    "content": prompts.build_repair_prompt(str(exc)),
                }
            )
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=tools.openai_tools_schema(),
            )
            text = response.choices[0].message.content or ""
    raise last_error  # type: ignore[misc]


async def analyze_product(
    product_id: int,
    store_id: int,
    db: Any,
    client: AsyncOpenAI | None = None,
) -> AIRecommendationResponse:
    """Полный цикл анализа товара: tool calls → финальный JSON (§3.2.1)."""
    client = client or make_client()
    if client is None:
        raise RuntimeError(
            "LLM API не настроен: заполни LLM_API_URL / LLM_API_KEY в .env"
        )
    messages: list[dict] = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.build_analysis_prompt(product_id),
        },
    ]
    used_tools: list[str] = []
    content = ""
    for _ in range(MAX_TOOL_ITERATIONS):
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=tools.openai_tools_schema(),
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        if not tool_calls:
            content = message.content or ""
            break
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )
        for item in await _execute_tool_calls(tool_calls, db):
            used_tools.append(item["name"])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item["tool_call_id"],
                    "content": json.dumps(
                        item["result"], ensure_ascii=False, default=str
                    ),
                }
            )
    else:
        raise RuntimeError(
            f"Агент не вышел к финальному ответу за {MAX_TOOL_ITERATIONS} "
            "итераций tool calls"
        )

    recommendation = await _parse_with_repair(client, messages, content, db)
    if used_tools:  # аудит: реальный список вызовов, а не память LLM
        recommendation.tool_calls_used = used_tools
    return recommendation
