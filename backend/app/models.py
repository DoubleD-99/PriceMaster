"""ORM-модели (SQLAlchemy 2.0) — 6 таблиц по ТЗ, раздел 4.

Модели:
- Product            -> products            (справочник товаров)
- Inventory          -> inventory           (текущие остатки)
- SalesHistory       -> sales_history       (история продаж)
- PriceHistory       -> price_history       (история изменений цен)
- ExternalFactor     -> external_factors    (внешние факторы: погода/праздник/demand_multiplier)
- PriceRecommendation-> price_recommendations (рекомендации агента)

Колонки, типы и связи — строго по ТЗ:
price_history.recommendation_id — FK на price_recommendations, nullable
(ручное изменение цены администратором оставляет поле пустым).
"""