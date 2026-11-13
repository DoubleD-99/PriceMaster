"""Контракт HTTP API для параллельной разработки (SDD §6.4–6.5)."""

from backend.app.main import app
from backend.app.schemas import (
    ErrorResponse,
    InventoryAlertsOut,
    RecommendationGenerateRequest,
    RecommendationOut,
)


def test_iteration2_paths_are_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/inventory/alerts" in paths
    assert "/recommendations/generate" in paths
    assert "/recommendations" in paths
    assert "/recommendations/{recommendation_id}/accept" in paths
    assert "/recommendations/{recommendation_id}/reject" in paths


def test_recommendation_contract_fields() -> None:
    assert set(RecommendationOut.model_fields) == {
        "id",
        "product_id",
        "store_id",
        "action_type",
        "recommended_value",
        "reasoning",
        "confidence",
        "status",
        "expected_impact",
        "created_at",
    }
    assert RecommendationGenerateRequest().limit == 10
    assert RecommendationGenerateRequest().product_id is None


def test_alert_and_error_contract_fields() -> None:
    assert set(InventoryAlertsOut.model_fields) == {"expiring_soon", "low_stock"}
    assert set(ErrorResponse.model_fields) == {"error_code", "message", "details"}
