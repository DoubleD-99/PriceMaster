"""HTTP-клиент к backend API (httpx).

Инкапсулирует запросы, которые делает бот:
- get_recommendations(status=...)  — GET /recommendations;
- get_products()                  — GET /products;
- get_price_history(product_id)   — GET /price-history/{product_id};
- post_sale(...)                  — POST /sales (при необходимости).

Базовый URL берётся из config.API_URL, таймаут из config.API_TIMEOUT.
Ошибки сети/API превращаются в понятные сообщения для пользователя.
"""
