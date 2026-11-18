"""Pydantic-схемы запросов и ответов API (SDD, раздел 3.1, schemas/).

Валидируемые модели для эндпоинтов SDD §6:
- LoginRequest / TokenResponse  — POST /auth/login;
- StoreOut                      — GET  /stores;
- ProductOut                    — GET  /products;
- InventoryOut                  — GET  /inventory;
- ReceivingCreate / ReceivingResult — POST /wms/receiving;
- WriteOffCreate / WriteOffResult   — POST /wms/write-off;
- InventoryAlertsOut            — GET  /inventory/alerts;
- RecommendationGenerateRequest / RecommendationOut — /recommendations;
- ErrorResponse                 — единый формат ошибок.

Схемы переиспользуются роутерами (api/v1) и агентом (services/ai)
для типобезопасного обмена.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# =========================
# AUTH
# =========================


class LoginRequest(BaseModel):
    access_key: str


class UserInfo(BaseModel):
    user_id: int
    username: str
    store_ids: list[int]


class TokenResponse(BaseModel):
    token: str
    user_info: UserInfo


# =========================
# STORES
# =========================


class StoreCreate(BaseModel):
    name: str
    address: str
    city: str


class StoreOut(BaseModel):
    id: int
    name: str
    address: str
    city: str

    model_config = ConfigDict(from_attributes=True)


# =========================
# PRODUCTS
# =========================


class ProductCreate(BaseModel):
    name: str
    category: str
    base_cost: Decimal
    shelf_life_days: int
    min_stock: int = 0


class ProductOut(BaseModel):
    id: int
    name: str
    category: str
    base_cost: Decimal
    shelf_life_days: int
    min_stock: int

    model_config = ConfigDict(from_attributes=True)


# =========================
# STORE PRODUCTS
# =========================


class StoreProductCreate(BaseModel):
    product_id: int
    store_id: int
    current_price: Decimal
    is_active: bool = True


class StoreProductOut(BaseModel):
    id: int
    product_id: int
    store_id: int
    current_price: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# =========================
# BARCODES
# =========================


class BarcodeCreate(BaseModel):
    product_id: int
    code: str


class BarcodeOut(BaseModel):
    id: int
    product_id: int
    code: str

    model_config = ConfigDict(from_attributes=True)


# =========================
# INVENTORY
# =========================


class InventoryOut(BaseModel):
    id: int
    product_id: int
    store_id: int
    quantity: int
    batch_date: date
    expiry_date: date

    model_config = ConfigDict(from_attributes=True)


# =========================
# WMS
# =========================


class ReceivingCreate(BaseModel):
    product_id: int
    quantity: int
    batch_date: date
    expiry_date: date


class WriteOffCreate(BaseModel):
    product_id: int
    quantity: int
    reason: str


class ReceivingResult(BaseModel):
    batch: InventoryOut
    quantity_added: int


class WriteOffBatch(BaseModel):
    batch_id: int
    expiry_date: date
    quantity: int


class WriteOffResult(BaseModel):
    product_id: int
    store_id: int
    quantity: int
    reason: str
    batches: list[WriteOffBatch]


# =========================
# SALES
# =========================


class SaleCreate(BaseModel):
    product_id: int
    store_id: int
    quantity_sold: int
    sale_price: Decimal


class SaleOut(BaseModel):
    id: int
    product_id: int
    store_id: int
    quantity_sold: int
    sale_price: Decimal
    sale_date: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# PRICE HISTORY
# =========================


class PriceHistoryOut(BaseModel):
    id: int
    product_id: int
    store_id: int
    old_price: Decimal
    new_price: Decimal
    changed_at: datetime
    recommendation_id: int | None

    model_config = ConfigDict(from_attributes=True)


# =========================
# RECOMMENDATIONS
# =========================

RecommendationAction = Literal["price_change", "reorder", "write_off"]
RecommendationStatus = Literal["pending", "accepted", "rejected"]


class RecommendationGenerateRequest(BaseModel):
    product_id: int | None = Field(
        default=None,
        description="Конкретный товар; без него pipeline выбирает кандидатов.",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Максимум кандидатов при пакетном анализе.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"product_id": 1},
                {"limit": 5},
            ]
        }
    )


class RecommendationOut(BaseModel):
    id: int
    product_id: int
    store_id: int
    action_type: RecommendationAction
    recommended_value: Decimal
    reasoning: str
    confidence: float
    status: RecommendationStatus
    expected_impact: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# ALERTS
# =========================


class ExpiringBatchAlert(BaseModel):
    product_id: int
    batch_id: int
    expiry_date: date
    days_left: int


class LowStockAlert(BaseModel):
    product_id: int
    quantity: int
    min_stock: int


class InventoryAlertsOut(BaseModel):
    expiring_soon: list[ExpiringBatchAlert]
    low_stock: list[LowStockAlert]


# =========================
# ANALYTICS
# =========================


class SalesSummaryOut(BaseModel):
    total_revenue: Decimal
    total_quantity: int
    sales_count: int
    average_check: Decimal


class SalesByDayOut(BaseModel):
    date: date
    revenue: Decimal
    quantity: int
    sales_count: int
    average_check: Decimal


class SalesByProductOut(BaseModel):
    product_id: int
    revenue: Decimal
    quantity: int
    sales_count: int
    average_check: Decimal


class SalesAnalyticsOut(BaseModel):
    summary: SalesSummaryOut
    by_day: list[SalesByDayOut]
    by_product: list[SalesByProductOut]


# =========================
# ERRORS
# =========================


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
