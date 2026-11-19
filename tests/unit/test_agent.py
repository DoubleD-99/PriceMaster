"""Unit-тесты цикла агента (SDD §3.2.1, §6.1, §8; §7.1 - LLM замокан).

- parse_recommendation: валидный JSON, ```json-блок, битый JSON,
  выход за рамки схемы (confidence, action_type);
- analyze_product: цикл LLM -> tool -> LLM -> финальный JSON с мок-клиентом;
  tool_calls_used перезаписывается реальным списком (аудит);
- retry при битом первом ответе (repair в messages);
- принудительный финальный JSON без tools на последней итерации;
- RuntimeError при ненастроенном LLM.
"""

import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.db.session import SessionLocal
from backend.app.schemas.ai import AIRecommendationResponse
from backend.app.services.ai import agent

VALID_JSON = json.dumps(
    {
        "action_type": "price_change",
        "recommended_value": 99.99,
        "reasoning": "Срок годности мал, остаток есть - рекомендуем снизить цену.",
        "confidence": 0.8,
        "expected_impact": 360.0,
        "tool_calls_used": [],
    },
    ensure_ascii=False,
)


def _llm_response(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=tool_calls)
            )
        ]
    )


def _tool_call(name: str, arguments: str, call_id: str = "call_1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _client(side_effect: list) -> SimpleNamespace:
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=side_effect))
        )
    )


# --------------------------------------------------------------------- парсер


def test_parse_valid_json() -> None:
    parsed = agent.parse_recommendation(VALID_JSON)
    assert parsed.action_type == "price_change"
    assert parsed.confidence == 0.8


def test_parse_json_in_code_fence() -> None:
    parsed = agent.parse_recommendation(f"```json\n{VALID_JSON}\n```")
    assert parsed.recommended_value == 100.0


def test_parse_broken_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        agent.parse_recommendation("не json вовсе")


def test_parse_confidence_out_of_range() -> None:
    data = json.loads(VALID_JSON)
    data["confidence"] = 1.5
    with pytest.raises(Exception) as exc_info:
        agent.parse_recommendation(json.dumps(data))
    assert "confidence" in str(exc_info.value)


def test_parse_bad_action_type() -> None:
    data = json.loads(VALID_JSON)
    data["action_type"] = "giveaway"
    with pytest.raises(Exception) as exc_info:
        agent.parse_recommendation(json.dumps(data))
    assert "action_type" in str(exc_info.value)


def test_parse_numeric_fields_from_tool_objects() -> None:
    data = json.loads(VALID_JSON)
    data["recommended_value"] = {"new_price": 120.56, "current_price": 130.0}
    data["expected_impact"] = {"expected_impact": -12.56, "new_price": 120.56}
    parsed = agent.parse_recommendation(json.dumps(data))
    assert parsed.recommended_value == 120.6
    assert parsed.expected_impact == -12.6


def test_parse_long_reasoning_is_shortened() -> None:
    data = json.loads(VALID_JSON)
    data["reasoning"] = "Слишком длинное объяснение. " * 40
    parsed = agent.parse_recommendation(json.dumps(data))
    assert len(parsed.reasoning) <= 500
    assert parsed.reasoning.endswith("...")


def test_parse_json_surrounded_by_text() -> None:
    parsed = agent.parse_recommendation(
        f"Вот ответ агента:\n{VALID_JSON}\nНадеюсь, помогло."
    )
    assert parsed.action_type == "price_change"


def test_request_extras_disable_groq_reasoning(monkeypatch) -> None:
    monkeypatch.setattr(agent.settings, "LLM_API_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(agent.settings, "LLM_MODEL", "openai/gpt-oss-20b")
    extras = agent._request_extras()
    assert extras["extra_body"]["reasoning_effort"] == "low"
    assert extras["extra_body"]["include_reasoning"] is False


# --------------------------------------------------------------------- цикл


async def test_analyze_product_tool_loop(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    tool_call = _tool_call(
        "get_stock_level",
        json.dumps({"product_id": product_id, "store_id": store_id}),
    )
    client = _client(
        [
            _llm_response(tool_calls=[tool_call]),
            _llm_response(content=VALID_JSON),
        ]
    )
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert isinstance(result, AIRecommendationResponse)
    # аудит: реальный список вызванных tools, не ответ LLM
    assert result.tool_calls_used == ["get_stock_level"]
    assert client.chat.completions.create.await_count == 2
    sent_messages = client.chat.completions.create.await_args_list[0].kwargs["messages"]
    user_text = sent_messages[1]["content"]
    assert f"store_id={store_id}" in user_text
    assert f"product_id={product_id}" in user_text or f"id={product_id}" in user_text
    assert "Сегодня:" in user_text
    assert re.search(r"\d{4}-\d{2}-\d{2}", user_text)


async def test_analyze_product_forces_final_answer(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    args = json.dumps({"product_id": product_id, "store_id": store_id})
    client = _client(
        [
            _llm_response(
                tool_calls=[_tool_call("get_stock_level", args, f"call_{idx}")]
            )
            for idx in range(agent.MAX_TOOL_ITERATIONS - 1)
        ]
        + [_llm_response(content=VALID_JSON)]
    )
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert result.action_type == "price_change"
    assert client.chat.completions.create.await_count == agent.MAX_TOOL_ITERATIONS
    last_call = client.chat.completions.create.await_args_list[-1].kwargs
    assert last_call["tools"]
    assert any(
        "Инструменты больше не вызывай" in str(m.get("content", ""))
        for m in last_call["messages"]
    )


async def test_analyze_product_empty_answer_nudges_model(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    client = _client([_llm_response(content=""), _llm_response(content=VALID_JSON)])
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert result.action_type == "price_change"
    messages = client.chat.completions.create.await_args_list[1].kwargs["messages"]
    assert any("Ответ пустой" in str(m.get("content", "")) for m in messages)


async def test_analyze_product_repair_retry(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    client = _client(
        [
            _llm_response(content="``` не тот JSON"),
            _llm_response(content=VALID_JSON),
        ]
    )
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert result.action_type == "price_change"
    # в messages repair и объяснение ошибки
    repair_call = client.chat.completions.create.await_args_list[1].kwargs
    sent_messages = repair_call["messages"]
    assert any(
        "не прошёл валидацию" in str(m.get("content", "")) for m in sent_messages
    )
    assert "tools" not in repair_call


async def test_analyze_product_broken_tool_args(shop) -> None:
    """Аргументы-битые в tool_calls -> ошибка в tool-результат, цикл жив."""
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    tool_call = _tool_call("get_stock_level", "не json")
    client = _client(
        [
            _llm_response(tool_calls=[tool_call]),
            _llm_response(content=VALID_JSON),
        ]
    )
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert result.tool_calls_used == ["get_stock_level"]


async def test_analyze_product_tool_not_allowed(shop) -> None:
    """Вызов вне whitelist попадает в tool-результат как ошибка."""
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    tool_call = _tool_call("delete_all_tables", "{}")
    client = _client(
        [
            _llm_response(tool_calls=[tool_call]),
            _llm_response(content=VALID_JSON),
        ]
    )
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert result.tool_calls_used == ["delete_all_tables"]


async def test_analyze_product_requires_llm_config(monkeypatch) -> None:
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "LLM_API_URL", "")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    with pytest.raises(RuntimeError, match="не настроен"):
        await agent.analyze_product(1, 1, db=None)
