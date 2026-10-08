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
