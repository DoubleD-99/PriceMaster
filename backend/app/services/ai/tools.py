"""Инструменты (Tools) агента — SDD §3.2.2, §3.2.3.

Единственный способ получить числа для LLM: агент вызывает эти функции и
вставляет готовые значения в контекст. Самостоятельно LLM не вычисляет
ничего (docs/agents.md, правило 2).

Реестр декораторный (Tool Registry Pattern, §3.2.2): функция, оформленная
@tool, попадает в REGISTRY и в whitelist для LLM — вызвать можно только её
(§3.2.5). Сигнатуры — Pydantic-модели (ADR-03); OpenAI-совместимый API
получает их как JSON Schema через openai_tools_schema().

Список (§3.2.3):
- get_stock_level            — остатки по партиям + дни до истечения;
- get_sales_trend            — средний спрос и тренд за N дней;
- check_external_factors     — погода, праздник, demand_multiplier;
- calculate_reorder_amount   — объём закупки (calculations.py);
- calculate_margin_impact    — ожидаемый эффект смены цены (calculations.py).

Все запросы к БД — read-only SELECT с фильтрацией по store_id (изоляция
магазинов, §3.4); данные инъецируются снаружи (db: AsyncSession), чтобы
эндпоинт /recommendations/generate (Итерация 2) переиспользовал сессию.
"""

import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ExternalFactor, Inventory, Product, SalesHistory
from backend.app.models import StoreProduct as StoreProductModel
from backend.app.services import calculations

# Hard limit на выполнение одного tool call (SDD §3.2.5).
TOOL_TIMEOUT_SECONDS = 10.0


class ToolSpec:
    """Описание одного инструмента: имя, промпт-описание, Pydantic-аргументы."""

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: type[BaseModel],
        func: Callable[..., Coroutine[Any, Any, dict]],
    ) -> None:
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.func = func

    def openai_schema(self) -> dict:
        """JSON Schema аргументов в формате OpenAI function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            },
        }


REGISTRY: dict[str, ToolSpec] = {}


def tool(
    name: str, description: str, args_schema: type[BaseModel]
) -> Callable[..., Coroutine[Any, Any, dict]]:
    """Декоратор регистрации инструмента (Tool Registry, §3.2.2)."""

    def decorator(func: Coroutine | Callable) -> Callable:
        REGISTRY[name] = ToolSpec(name, description, args_schema, func)
        return func

    return decorator


# --------------------------------------------------------------------- аргументы


class GetStockLevelArgs(BaseModel):
    product_id: int = Field(description="ID товара")
    store_id: int = Field(description="ID магазина")


class GetSalesTrendArgs(BaseModel):
    product_id: int = Field(description="ID товара")
    store_id: int = Field(description="ID магазина")
    days: int = Field(default=calculations.FORECAST_DAYS, ge=1, le=365)


class CheckExternalFactorsArgs(BaseModel):
    store_id: int = Field(description="ID магазина")
    date: str = Field(description="Дата анализа в формате YYYY-MM-DD")


class CalculateReorderAmountArgs(BaseModel):
    product_id: int = Field(description="ID товара")
    store_id: int = Field(description="ID магазина")


class CalculateMarginImpactArgs(BaseModel):
    product_id: int = Field(description="ID товара")
    store_id: int = Field(description="ID магазина")
    new_price: Decimal = Field(gt=0, description="Предлагаемая новая цена")


# --------------------------------------------------------------------- вызов


async def call_tool(name: str, args: dict, db: AsyncSession) -> dict:
    """Выполнить инструмент из whitelist: валидация аргументов + timeout.

    Ошибка данных (нет товара и т.п.) возвращается словарём с error_code,
    чтобы LLM увидела её в tool-результате и не домысливала цифры.
    """
    spec = REGISTRY.get(name)
    if spec is None:
        return {
            "error_code": "TOOL_NOT_ALLOWED",
            "message": f"Инструмент '{name}' не в whitelist",
        }
    try:
        parsed = spec.args_schema.model_validate(args)
    except ValidationError as exc:
        return {"error_code": "TOOL_BAD_ARGUMENTS", "message": str(exc)}
    try:
        result = await asyncio.wait_for(
            spec.func(parsed, db), timeout=TOOL_TIMEOUT_SECONDS
        )
    except TimeoutError:
        return {
            "error_code": "TOOL_TIMEOUT",
            "message": f"Инструмент '{name}' не уложился в {TOOL_TIMEOUT_SECONDS} c",
        }
    return result


def openai_tools_schema() -> list[dict]:
    """Whitelist инструментов в формате OpenAI API (только реестр, §3.2.5)."""
    return [spec.openai_schema() for spec in REGISTRY.values()]


# --------------------------------------------------------------------- данные


async def _avg_daily_sales(
    db: AsyncSession, product_id: int, store_id: int, days: int
) -> Decimal:
    """Средний дневной спрос за последние days дней (0 — продаж нет)."""
    today = datetime.now(UTC).date()
    since = today.fromordinal(today.toordinal() - days)
    rows = (
        await db.scalars(
            select(SalesHistory.quantity_sold).where(
                SalesHistory.product_id == product_id,
                SalesHistory.store_id == store_id,
                SalesHistory.sale_date >= since,
            )
        )
    ).all()
    if not rows:
        return Decimal(0)
    return Decimal(sum(rows)) / days


async def _total_stock(db: AsyncSession, product_id: int, store_id: int) -> int:
    """Суммарный остаток по всем непустым партиям товара в магазине."""
    rows = (
        await db.scalars(
            select(Inventory.quantity).where(
                Inventory.product_id == product_id,
                Inventory.store_id == store_id,
                Inventory.quantity > 0,
            )
        )
    ).all()
    return sum(rows)


async def _demand_multiplier(db: AsyncSession, store_id: int, day: date) -> Decimal:
    """Множитель спроса на дату; если записи нет — 1.0 (без фантазий)."""
    row = await db.scalar(
        select(ExternalFactor.demand_multiplier).where(
            ExternalFactor.store_id == store_id,
            ExternalFactor.date == day,
        )
    )
    return row if row is not None else Decimal(1)


# --------------------------------------------------------------------- tools


@tool(
    name="get_stock_level",
    description=(
        "Текущие остатки товара в магазине: суммарное количество, разбивка "
        "по партиям с датами годности и минимальный срок до истечения. "
        "Вызывай перед решением о скидке или закупке."
    ),
    args_schema=GetStockLevelArgs,
)
async def get_stock_level(args: GetStockLevelArgs, db: AsyncSession) -> dict:
    rows = (
        await db.execute(
            select(Inventory.quantity, Inventory.batch_date, Inventory.expiry_date)
            .where(
                Inventory.product_id == args.product_id,
                Inventory.store_id == args.store_id,
                Inventory.quantity > 0,
            )
            .order_by(Inventory.expiry_date)
        )
    ).all()
    today = datetime.now(UTC).date()
    batches = [
        {
            "batch_id": idx,
            "quantity": quantity,
            "batch_date": batch_date.isoformat(),
            "expiry_date": expiry.isoformat(),
            "days_to_expiry": (expiry - today).days,
        }
        for idx, (quantity, batch_date, expiry) in enumerate(rows, start=1)
    ]
    return {
        "product_id": args.product_id,
        "store_id": args.store_id,
        "total_quantity": sum(b["quantity"] for b in batches),
        "batches": batches,
        "min_days_to_expiry": min((b["days_to_expiry"] for b in batches), default=None),
    }


@tool(
    name="get_sales_trend",
    description=(
        "Динамика продаж товара за N дней: сумма, средний дневной спрос и "
        "тренд (растёт/падает/стабильно) по сравнению двух половин периода."
    ),
    args_schema=GetSalesTrendArgs,
)
async def get_sales_trend(args: GetSalesTrendArgs, db: AsyncSession) -> dict:
    today = datetime.now(UTC).date()
    since = today.fromordinal(today.toordinal() - args.days)
    rows = (
        await db.execute(
            select(SalesHistory.sale_date, SalesHistory.quantity_sold).where(
                SalesHistory.product_id == args.product_id,
                SalesHistory.store_id == args.store_id,
                SalesHistory.sale_date >= since,
            )
        )
    ).all()
    mid = args.days / 2
    first_half = sum(
        qty for sale_date, qty in rows if (sale_date.date() - since).days < mid
    )
    second_half = sum(
        qty for sale_date, qty in rows if (sale_date.date() - since).days >= mid
    )
    total = first_half + second_half
    if first_half > 0:
        change_pct = round((second_half - first_half) / first_half * 100, 1)
        if change_pct > 10:
            trend = "rising"
        elif change_pct < -10:
            trend = "falling"
        else:
            trend = "flat"
    else:
        change_pct = None
        trend = "no_data" if total == 0 else "flat"
    return {
        "product_id": args.product_id,
        "store_id": args.store_id,
        "days": args.days,
        "total_sold": total,
        "avg_daily_sales": round(total / args.days, 2),
        "trend": trend,
        "change_pct": change_pct,
    }


@tool(
    name="check_external_factors",
    description=(
        "Внешние факторы на дату: погода, праздник/выходной и множитель "
        "спроса demand_multiplier (>1 — спрос выше обычного)."
    ),
    args_schema=CheckExternalFactorsArgs,
)
async def check_external_factors(
    args: CheckExternalFactorsArgs, db: AsyncSession
) -> dict:
    try:
        day = date.fromisoformat(args.date)
    except ValueError:
        return {
            "error_code": "BAD_DATE",
            "message": f"Дата '{args.date}' не в формате YYYY-MM-DD",
        }
    row = (
        await db.execute(
            select(
                ExternalFactor.weather_condition,
                ExternalFactor.is_holiday,
                ExternalFactor.demand_multiplier,
            ).where(
                ExternalFactor.store_id == args.store_id,
                ExternalFactor.date == day,
            )
        )
    ).first()
    if row is None:
        return {
            "store_id": args.store_id,
            "date": args.date,
            "available": False,
            "demand_multiplier": 1.0,
            "note": "Нет данных за дату — считай множитель равным 1.0",
        }
    weather, is_holiday, multiplier = row
    return {
        "store_id": args.store_id,
        "date": args.date,
        "available": True,
        "weather_condition": weather,
        "is_holiday": is_holiday,
        "demand_multiplier": float(multiplier),
    }


@tool(
    name="calculate_reorder_amount",
    description=(
        "Объём закупки (штук) для пополнения склада: целевой остаток на срок "
        "поставки плюс минимальный остаток минус текущий остаток. Считает "
        "Python-функция — число НЕ придумывай, используй результат как есть."
    ),
    args_schema=CalculateReorderAmountArgs,
)
async def calculate_reorder_amount(
    args: CalculateReorderAmountArgs, db: AsyncSession
) -> dict:
    product = await db.get(Product, args.product_id)
    if product is None:
        return {
            "error_code": "PRODUCT_NOT_FOUND",
            "message": f"Товар id={args.product_id} не найден",
        }
    avg_daily = await _avg_daily_sales(
        db, args.product_id, args.store_id, calculations.FORECAST_DAYS
    )
    stock = await _total_stock(db, args.product_id, args.store_id)
    amount = calculations.reorder_amount(avg_daily, stock, min_stock=product.min_stock)
    return {
        "product_id": args.product_id,
        "store_id": args.store_id,
        "reorder_amount": amount,
        "unit": "шт",
        "current_stock": stock,
        "min_stock": product.min_stock,
        "avg_daily_sales": float(avg_daily),
        "lead_time_days": calculations.LEAD_TIME_DAYS,
    }


@tool(
    name="calculate_margin_impact",
    description=(
        "Ожидаемый эффект (в деньгах за горизонт прогноза) от смены цены на "
        "new_price при текущем спросе и внешних факторах. Считает "
        "Python-функция — число НЕ придумывай, используй результат как есть."
    ),
    args_schema=CalculateMarginImpactArgs,
)
async def calculate_margin_impact(
    args: CalculateMarginImpactArgs, db: AsyncSession
) -> dict:
    product = await db.get(Product, args.product_id)
    if product is None:
        return {
            "error_code": "PRODUCT_NOT_FOUND",
            "message": f"Товар id={args.product_id} не найден",
        }
    price_row = await db.scalar(
        select(StoreProductModel.current_price).where(
            StoreProductModel.product_id == args.product_id,
            StoreProductModel.store_id == args.store_id,
            StoreProductModel.is_active.is_(True),
        )
    )
    if price_row is None:
        return {
            "error_code": "PRICE_NOT_FOUND",
            "message": (
                f"Для товара id={args.product_id} в магазине "
                f"id={args.store_id} нет активной цены"
            ),
        }
    avg_daily = await _avg_daily_sales(
        db, args.product_id, args.store_id, calculations.FORECAST_DAYS
    )
    multiplier = await _demand_multiplier(db, args.store_id, datetime.now(UTC).date())
    impact = calculations.margin_impact(
        product.base_cost,
        price_row,
        args.new_price,
        avg_daily,
        multiplier,
    )
    return {
        "product_id": args.product_id,
        "store_id": args.store_id,
        "base_cost": float(product.base_cost),
        "current_price": float(price_row),
        "new_price": float(args.new_price),
        "avg_daily_sales": float(avg_daily),
        "demand_multiplier": float(multiplier),
        "forecast_days": calculations.FORECAST_DAYS,
        "forecast_sales": float(calculations.forecast_sales(avg_daily, multiplier)),
        "expected_impact": float(impact),
    }
