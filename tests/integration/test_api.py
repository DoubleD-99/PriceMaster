"""Integration-тесты REST API (SDD, Приложение A, раздел 5).

Проверяют на тестовой БД:
- POST /auth/login               — выдача JWT по access_key;
- GET  /stores                   — список магазинов;
- GET  /products                 — список товаров;
- GET  /inventory                — остатки фильтра по X-Store-ID;
- POST /wms/receiving            — приёмка: партия + остаток;
- POST /wms/write-off            — списание с причиной (FIFO);
- GET  /barcodes/{code}          — поиск товара по ШК;
- GET  /recommendations          — список рекомендаций;
- POST /recommendations/generate — запуск анализа (LLM замокан);
- POST /recommendations/{id}/accept — принятие: цена + price_history;
- GET  /analytics/sales          — агрегация продаж.

Клиент — httpx.AsyncClient против FastAPI-приложения из backend.app.main.
"""
