"""Pydantic-схемы запросов и ответов API.

Здесь описываются валидируемые модели данных:
- Product — ответ GET /products (товар + текущий остаток);
- SaleCreate / SaleOut — тело и ответ POST /sales;
- RecommendationOut — ответ GET /recommendations;
- PriceHistoryOut — элемент ответа GET /price-history/{product_id}.

Схемы переиспользуются роутерами и агентом (ai_agent) для типобезопасного обмена.
"""