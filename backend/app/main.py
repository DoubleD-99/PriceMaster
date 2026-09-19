"""Входная точка FastAPI-приложения.

Здесь создаётся экземпляр `app`, подключаются все роутеры (products, sales,
recommendations, price_history), веб-дашборд (FastAPI templates) и, при наличии
реализации, `seed_db` для работы в Docker.

Запуск (из корня репозитория):
    python -m uvicorn backend.app.main:app --reload

Документация API: http://127.0.0.1:8000/docs
"""
