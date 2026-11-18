"""Pydantic-схема AI-агента.

AIRecommendationResponse - контракт финального ответа агента (SDD §6.1):
агент должен вернуть JSON этой формы; парсер в agent.py валидирует через
Pydantic и выбрасывает ValidationError при битом ответе (retry - §8).
Числовые поля вычисляются значениями из tools, reasoning - текст LLM.
"""

from typing import Literal

from pydantic import BaseModel, Field


class AIRecommendationResponse(BaseModel):
    action_type: Literal["price_change", "reorder", "write_off"]
    recommended_value: float
    reasoning: str = Field(max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    expected_impact: float
    tool_calls_used: list[str] = Field(default_factory=list)
