"""Рекомендации: выбор кандидатов, генерация, accept/reject.

Бизнес-логика HTTP-слоя `/recommendations` (SDD §6.4). Расчёты выполняет
`services/ai`, запись цены — только `accept_recommendation` (D-08/D-09).
"""

import json
from decimal import Decimal

from openai import APIError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    PriceHistory,
    PriceRecommendation,
    Product,
    StoreProduct,
)
from backend.app.services import wms
from backend.app.services.ai import agent
from backend.app.services.calculations import round_money


class RecommendationError(Exception):
    """Ошибка сценария рекомендаций; роутер отдаёт её в формате SDD §6.2."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def list_recommendations(
    db: AsyncSession,
    *,
    store_id: int,
    status: str | None = None,
) -> list[PriceRecommendation]:
    """Рекомендации магазина, новые сверху; опциональный фильтр по статусу."""
    stmt = select(PriceRecommendation).where(PriceRecommendation.store_id == store_id)
    if status is not None:
        stmt = stmt.where(PriceRecommendation.status == status)
    stmt = stmt.order_by(
        PriceRecommendation.created_at.desc(),
        PriceRecommendation.id.desc(),
    )
    return list((await db.scalars(stmt)).all())


async def _get_pending(
    db: AsyncSession,
    *,
    store_id: int,
    recommendation_id: int,
) -> PriceRecommendation:
    recommendation = await db.scalar(
        select(PriceRecommendation).where(
            PriceRecommendation.id == recommendation_id,
            PriceRecommendation.store_id == store_id,
        )
    )
    if recommendation is None:
        raise RecommendationError(
            "RECOMMENDATION_NOT_FOUND",
            f"Рекомендация id={recommendation_id} не найдена",
            status_code=404,
        )
    if recommendation.status != "pending":
        raise RecommendationError(
            "RECOMMENDATION_ALREADY_PROCESSED",
            "Рекомендация уже обработана",
            status_code=409,
            details={"status": recommendation.status},
        )
    return recommendation


async def accept_recommendation(
    db: AsyncSession,
    *,
    store_id: int,
    recommendation_id: int,
) -> PriceRecommendation:
    """Принять рекомендацию; цену меняет только `price_change` (D-08)."""
    recommendation = await _get_pending(
        db, store_id=store_id, recommendation_id=recommendation_id
    )
    if recommendation.action_type == "price_change":
        store_product = await db.scalar(
            select(StoreProduct).where(
                StoreProduct.store_id == store_id,
                StoreProduct.product_id == recommendation.product_id,
                StoreProduct.is_active.is_(True),
            )
        )
        if store_product is None:
            raise RecommendationError(
                "STORE_PRODUCT_NOT_FOUND",
                "Цена товара в магазине не найдена",
                status_code=404,
                details={"product_id": recommendation.product_id},
            )
        old_price = round_money(store_product.current_price)
        new_price = round_money(recommendation.recommended_value)
        store_product.current_price = new_price
        db.add(
            PriceHistory(
                product_id=recommendation.product_id,
                store_id=store_id,
                old_price=old_price,
                new_price=new_price,
                recommendation_id=recommendation.id,
            )
        )
    recommendation.status = "accepted"
    await db.flush()
    return recommendation


async def reject_recommendation(
    db: AsyncSession,
    *,
    store_id: int,
    recommendation_id: int,
) -> PriceRecommendation:
    """Отклонить рекомендацию без изменения цены (D-09)."""
    recommendation = await _get_pending(
        db, store_id=store_id, recommendation_id=recommendation_id
    )
    recommendation.status = "rejected"
    await db.flush()
    return recommendation


async def select_candidates(
    db: AsyncSession,
    *,
    store_id: int,
    product_id: int | None,
) -> list[int]:
    """Кандидаты: конкретный товар или алёрты по остаткам/срокам."""
    if product_id is not None:
        product = await db.get(Product, product_id)
        if product is None:
            raise RecommendationError(
                "PRODUCT_NOT_FOUND",
                f"Товар id={product_id} не найден",
                status_code=404,
            )
        return [product_id]

    alerts = await wms.alerts(db, store_id=store_id)
    existing = set(
        (
            await db.scalars(
                select(PriceRecommendation.product_id).where(
                    PriceRecommendation.store_id == store_id,
                )
            )
        ).all()
    )
    seen: set[int] = set()
    candidates: list[int] = []
    for row in alerts["expiring_soon"] + alerts["low_stock"]:
        candidate = row["product_id"]
        if candidate not in seen and candidate not in existing:
            seen.add(candidate)
            candidates.append(candidate)
    candidates.sort()
    return candidates


async def generate_recommendations(
    db: AsyncSession,
    *,
    store_id: int,
    product_id: int | None,
    limit: int,
) -> list[PriceRecommendation]:
    """Проанализировать кандидатов и сохранить `pending`-рекомендации."""
    candidates = await select_candidates(db, store_id=store_id, product_id=product_id)
    created: list[PriceRecommendation] = []
    errors: list[RecommendationError] = []
    for candidate_id in candidates:
        if product_id is None and len(created) >= limit:
            break
        try:
            result = await agent.analyze_product(candidate_id, store_id, db)
        except RuntimeError as exc:
            code = "LLM_NOT_CONFIGURED" if "не настроен" in str(exc) else "LLM_ERROR"
            err = RecommendationError(
                code, str(exc), status_code=503 if code == "LLM_NOT_CONFIGURED" else 502
            )
            if product_id is not None or code == "LLM_NOT_CONFIGURED":
                raise err from exc
            errors.append(err)
            continue
        except APIError as exc:
            if getattr(exc, "status_code", None) == 429:
                raise RecommendationError(
                    "LLM_RATE_LIMITED",
                    "Лимит запросов к LLM исчерпан. Повторите попытку позже.",
                    status_code=503,
                ) from exc
            err = RecommendationError(
                "LLM_ERROR",
                "Ошибка при обращении к LLM. Повторите попытку позже.",
                status_code=502,
            )
            if product_id is not None:
                raise err from exc
            errors.append(err)
            continue
        except (json.JSONDecodeError, ValidationError) as exc:
            err = RecommendationError(
                "LLM_INVALID_RESPONSE",
                "LLM не вернула валидный JSON после repair-retry",
                status_code=502,
            )
            if product_id is not None:
                raise err from exc
            errors.append(err)
            continue

        recommended_value = round_money(Decimal(str(result.recommended_value)))
        recommendation = PriceRecommendation(
            product_id=candidate_id,
            store_id=store_id,
            action_type=result.action_type,
            recommended_value=recommended_value,
            reasoning=result.reasoning,
            confidence=result.confidence,
            status=("pending" if recommended_value > 0 else "rejected"),
            expected_impact=round_money(Decimal(str(result.expected_impact))),
        )
        db.add(recommendation)
        created.append(recommendation)
    if product_id is None and not created and errors:
        raise errors[0]
    await db.flush()
    return created
