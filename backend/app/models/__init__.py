"""ORM-модели (SQLAlchemy 2.0) — 9 таблиц (SDD, Приложение A, раздел 12).

Модели:
- Store            -> stores              (магазины, 2–3 шт.)
- Product          -> products            (общий каталог товаров)
- Barcode          -> barcodes            (штрихкоды товаров)
- StoreProduct     -> store_products      (цены и min_stock на магазин)
- Inventory        -> inventory           (остатки, партии batch_date/expiry_date)
- SalesHistory     -> sales_history       (история продаж)
- PriceHistory     -> price_history       (история изменений цен)
- ExternalFactor   -> external_factors    (погода/праздник/demand_multiplier)
- PriceRecommendation -> price_recommendations (рекомендации агента)

Колонки, типы и связи — строго по SDD, Приложение A, раздел 12:
- store_id (FK) во всех транзакционных таблицах: inventory, sales_history,
  price_history, price_recommendations (изоляция магазинов — раздел 7);
- price_history.recommendation_id — FK на price_recommendations, nullable
  (ручное изменение цены оставляет поле пустым).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    base_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shelf_life_days: Mapped[int] = mapped_column(Integer)
    min_stock: Mapped[int] = mapped_column(Integer, default=0)


class StoreProduct(Base):
    __tablename__ = "store_products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Barcode(Base):
    __tablename__ = "barcodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)


class Inventory(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    batch_date: Mapped[date] = mapped_column(Date, index=True)
    expiry_date: Mapped[date] = mapped_column(Date)


class SalesHistory(Base):
    __tablename__ = "sales_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    quantity_sold: Mapped[int] = mapped_column(Integer)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sale_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PriceHistory(Base):
    __tablename__ = "price_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    recommendation_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_recommendations.id"), nullable=True
    )


class ExternalFactor(Base):
    __tablename__ = "external_factors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    date: Mapped[date] = mapped_column(Date)
    weather_condition: Mapped[str] = mapped_column(String(50))
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    demand_multiplier: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=1.0)


class PriceRecommendation(Base):
    __tablename__ = "price_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    action_type: Mapped[str] = mapped_column(String(50))
    recommended_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    reasoning: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    expected_impact: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
