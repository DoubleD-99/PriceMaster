"""Unit-тесты цикла агента (SDD §3.2.1, §6.1, §9; §7.1 — LLM замокан).

- parse_recommendation: валидный JSON, ```json-обёртка, битый JSON,
  выход за рамки схемы (confidence, action_type);
- analyze_product: цикл LLM -> tool -> LLM -> финальный JSON с мок-клиентом;
  tool_calls_used перезаписывается реальным списком (аудит);
- retry при битом первом ответе (ремарка в messages);
- RuntimeError при ненастроенной LLM.
"""

import json
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
        "reasoning": "Спрос вырос, остаток мал — рекомендую поднять цену.",
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
    assert parsed.recommended_value == 99.99


def test_parse_broken_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        agent.parse_recommendation("не json вообще")


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
    # аудит: реальный список вызванных tools, а не поле из ответа LLM
    assert result.tool_calls_used == ["get_stock_level"]
    assert client.chat.completions.create.await_count == 2


async def test_analyze_product_repair_retry(shop) -> None:
    store_id, product_id = shop["store_ids"][0], shop["product_ids"][0]
    client = _client(
        [
            _llm_response(content="``` это не JSON"),
            _llm_response(content=VALID_JSON),
        ]
    )
    async with SessionLocal() as session:
        result = await agent.analyze_product(
            product_id, store_id, session, client=client
        )
    assert result.action_type == "price_change"
    # в messages ремарка о невалидности
    sent_messages = client.chat.completions.create.await_args_list[1].kwargs["messages"]
    assert any(
        "не прошёл валидацию" in str(m.get("content", "")) for m in sent_messages
    )


async def test_analyze_product_broken_tool_args(shop) -> None:
    """Аргументы-мусор в tool_calls → ошибка в tool-результате, цикл жив."""
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
