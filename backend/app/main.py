"""Входная точка FastAPI-приложения (SDD, раздел 3.1).

Здесь создаётся экземпляр `app` и подключаются роутеры api/v1
(Приложение A, раздел 5): auth, stores, products, inventory, wms,
barcodes, recommendations, analytics — пути монтируются без общего
префикса, ровно как в спецификации.

Запуск (из корня репозитория):
    python -m uvicorn backend.app.main:app --reload

Документация API: http://127.0.0.1:8000/docs
"""
