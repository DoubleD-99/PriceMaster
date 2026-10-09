"""Pydantic-схемы запросов и ответов API (SDD, раздел 3.1, schemas/).

Валидируемые модели для эндпоинтов Приложения A, раздела 5:
- LoginRequest / TokenResponse  — POST /auth/login;
- StoreOut                      — GET  /stores;
- ProductOut                    — GET  /products;
- InventoryItemOut              — GET  /inventory;
- ReceivingRequest / WriteOffRequest — POST /wms/receiving, /wms/write-off;
- RecommendationOut             — GET  /recommendations;
- SaleOut                       — GET  /analytics/sales.

Схемы переиспользуются роутерами (api/v1) и агентом (services/ai)
для типобезопасного обмена.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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


class RecommendationOut(BaseModel):
    id: int
    product_id: int
    store_id: int
    action_type: str
    recommended_value: Decimal
    reasoning: str
    confidence: float
    status: str
    expected_impact: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
