"""Integration-тесты REST API (ТЗ раздел 3, критерии из раздела 6).

Проверяют на тестовой БД:
- GET  /products                 — список товаров с остатками;
- POST /sales                    — запись продажи + изменение остатка;
- GET  /recommendations          — последние советы агента;
- GET  /price-history/{id}       — история цен товара;
- GET  /dashboard                — отдаёт HTML-шаблон дашборда (200).

Клиент — httpx.AsyncClient против FastAPI-приложения из backend.app.main.
"""