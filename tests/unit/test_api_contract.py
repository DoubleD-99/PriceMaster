"""Контракт HTTP API для параллельной разработки (SDD §6.4–6.5)."""

from decimal import Decimal

from backend.app.main import app
from backend.app.schemas import (
    ErrorResponse,
    InventoryAlertsOut,
    ProductOut,
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
    assert "/products/{product_id}/price" in paths
    assert "/products/{product_id}/price-history" in paths


def test_money_fields_serialize_with_one_digit() -> None:
    product = ProductOut(
        id=1,
        name="Товар",
        category="Категория",
        base_cost=Decimal("12.34"),
        shelf_life_days=7,
        min_stock=1,
    )
    assert product.model_dump()["base_cost"] == Decimal("12.3")


def test_recommendation_contract_fields() -> None:
    assert set(RecommendationOut.model_fields) == {
        "id",
        "product_id",
        "store_id",
        "action_type",
        "recommended_value",
        "current_price",
        "current_stock",
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


def test_openapi_matches_runtime_header_and_error_contract() -> None:
    schema = app.openapi()
    error_ref = {"$ref": "#/components/schemas/ErrorResponse"}
    store_scoped = {
        "/inventory": "get",
        "/wms/receiving": "post",
        "/recommendations": "get",
        "/analytics/sales": "get",
    }
    for path, method in store_scoped.items():
        operation = schema["paths"][path][method]
        headers = [
            parameter
            for parameter in operation["parameters"]
            if parameter["name"] == "X-Store-ID"
        ]
        assert len(headers) == 1
        assert headers[0]["required"] is True
        assert (
            operation["responses"]["400"]["content"]["application/json"]["schema"]
            == error_ref
        )
    protected = schema["paths"]["/stores"]["get"]["responses"]
    assert protected["400"]["content"]["application/json"]["schema"] == error_ref
    assert protected["403"]["content"]["application/json"]["schema"] == error_ref
    validation = schema["paths"]["/auth/login"]["post"]["responses"]["422"]
    assert validation["content"]["application/json"]["schema"] == error_ref
    assert "HTTPValidationError" not in schema["components"]["schemas"]
