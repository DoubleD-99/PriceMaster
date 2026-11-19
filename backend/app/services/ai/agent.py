"""Оркестратор AI-агента: цикл Tool Calling (SDD §3.2.1).

Поток (вызывается из POST /recommendations/generate):
1. system (prompts.py) + user с контекстом -> chat.completions с tools=
   (whitelist из tools.REGISTRY, §3.2.2);
2. LLM возвращает tool_calls -> выполняем их через tools.call_tool
   (read-only доступ, timeout 10 c) -> результаты возвращаем модели;
3. повторяем до финального текстового ответа (не более MAX_TOOL_ITERATIONS);
4. парсим финальный JSON и валидируем AIRecommendationResponse (§6.1);
   при ValidationError / битом JSON - retry с уточнением (до 3 попыток, §8);
5. tool_calls_used перезаписывается реальным списком вызванных tools
   (поле для аудита - не доверяем модели).

Автоматическое применение цены не допускается: tools только читают, применение -
исключительно POST /recommendations/{id}/accept (§3.2.5).

Клиент LLM параметризуем (параметр client) - unit-тесты гоняют цикл с
моком, без реального API (§7.1).
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.models import Product
from backend.app.schemas.ai import AIRecommendationResponse
from backend.app.services.ai import prompts, tools
from backend.app.services.calculations import round_money

# Лимит последовательных вызовов tools в одном цикле (защита от зацикливания).
# Некоторые провайдеры вызывают инструменты по одному за ответ, поэтому 3 мало.
MAX_TOOL_ITERATIONS = 8
# Попытки починить невалидный JSON от LLM (см. «Итоговый JSON», §8).
MAX_REPAIR_ATTEMPTS = 3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)
logger.propagate = False

_RECOMMENDED_VALUE_KEYS = (
    "recommended_value",
    "new_price",
    "reorder_amount",
    "total_quantity",
    "quantity",
    "units",
)
_IMPACT_KEYS = ("expected_impact", "impact")


def _to_number(value: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ".").strip())
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in keys:
            if key in value:
                number = _to_number(value[key], keys)
                if number is not None:
                    return number
    return None


def _shorten_reasoning(value: Any) -> Any:
    if not isinstance(value, str) or len(value) <= 500:
        return value
    return value[:497].rstrip() + "..."


def _round_number(value: float) -> float:
    """Округлить числовое поле ответа LLM до одного знака."""
    return float(round_money(value))


def make_client() -> AsyncOpenAI | None:
    """Создать клиент внешнего OpenAI-совместимого API; None - если не настроен."""
    if not settings.LLM_API_URL or not settings.LLM_API_KEY:
        return None
    return AsyncOpenAI(
        base_url=settings.LLM_API_URL or None,
        api_key=settings.LLM_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
    )


def _request_extras() -> dict:
    """Не тратить Reasoning-токены GPT-OSS на Groq без нужды."""
    url = settings.LLM_API_URL.lower()
    model = settings.LLM_MODEL.lower()
    if "groq" in url and model.startswith("openai/gpt-oss"):
        return {
            "extra_body": {
                "reasoning_effort": "low",
                "include_reasoning": False,
            }
        }
    return {}


def _log_usage(response: Any, stage: str) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0)
    completion_tokens = getattr(usage, "completion_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", 0)
    logger.info(
        "llm tokens stage=%s model=%s prompt=%s completion=%s total=%s",
        stage,
        settings.LLM_MODEL,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        extra={
            "stage": stage,
            "model": settings.LLM_MODEL,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    )


def parse_recommendation(text: str) -> AIRecommendationResponse:
    """JSON из ответа LLM (часто в ```json-блоке) -> Pydantic (§6.1).

    Числовые поля, пришедшие объектами tools, приводятся к числу и округляются
    до одного знака; длинный reasoning обрезается до 500 символов. Битый JSON и
    нарушение остальной схемы -> json.JSONDecodeError / ValidationError, это
    ловит retry-цикл.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    data: Any = json.loads(cleaned)
    if isinstance(data, dict):
        data = dict(data)
        for field, keys in (
            ("recommended_value", _RECOMMENDED_VALUE_KEYS),
            ("expected_impact", _IMPACT_KEYS),
        ):
            if field in data:
                number = _to_number(data[field], keys)
                if number is not None:
                    data[field] = _round_number(number)
        if "reasoning" in data:
            data["reasoning"] = _shorten_reasoning(data["reasoning"])
    return AIRecommendationResponse.model_validate(data)


async def _execute_tool_calls(tool_calls: list[Any], db: Any) -> list[dict]:
    """Выполнить tool_calls из ответа LLM; аргументы-битые - ошибка в результат."""
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
    content: str,
) -> AIRecommendationResponse:
    """Retry-цикл парсинга: битый ответ -> отдельный запрос без истории tools."""
    text = content
    last_error: Exception | None = None
    for _ in range(MAX_REPAIR_ATTEMPTS):
        try:
            return parse_recommendation(text)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            repair_messages = [
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"{prompts.build_repair_prompt(str(exc))}\n"
                        f"Невалидный ответ: {text[:2000]}"
                    ),
                },
            ]
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=repair_messages,
                **_request_extras(),
            )
            _log_usage(response, "repair")
            text = response.choices[0].message.content or ""
    raise last_error  # type: ignore[misc]


async def analyze_product(
    product_id: int,
    store_id: int,
    db: Any,
    client: AsyncOpenAI | None = None,
) -> AIRecommendationResponse:
    """Полный цикл анализа товара: tool calls -> финальный JSON (§3.2.1)."""
    client = client or make_client()
    if client is None:
        raise RuntimeError(
            "LLM API не настроен: задайте LLM_API_URL / LLM_API_KEY в .env"
        )

    product_name = None
    if db is not None:
        product = await db.get(Product, product_id)
        if product is not None:
            product_name = getattr(product, "name", None)
    today = datetime.now(UTC).date().isoformat()

    messages: list[dict] = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": prompts.build_analysis_prompt(
                product_id, store_id, today, product_name
            ),
        },
    ]
    used_tools: list[str] = []
    content = ""
    for iteration in range(MAX_TOOL_ITERATIONS):
        final_attempt = iteration == MAX_TOOL_ITERATIONS - 1
        if final_attempt:
            messages.append({"role": "user", "content": prompts.build_final_prompt()})
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=tools.openai_tools_schema(),
            **_request_extras(),
        )
        _log_usage(response, f"tools_{iteration}")
        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        if not tool_calls:
            content = message.content or ""
            if content.strip() or final_attempt:
                break
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Ответ пустой. Продолжи сбор данных через tools или верни "
                        "финальный JSON."
                    ),
                }
            )
            continue
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
            f"Агент не дошёл до финального ответа за {MAX_TOOL_ITERATIONS} "
            "итераций tool calls"
        )

    recommendation = await _parse_with_repair(client, content)
    recommendation.tool_calls_used = used_tools
    return recommendation
