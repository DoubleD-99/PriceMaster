"""Пакет бэкенда PriceMaster.

Содержит:
- app/   — FastAPI-приложение (модели, схемы, роутеры, сервисы, шаблон дашборда);
- seed_db.py — скрипт наполнения БД синтетическими данными.

Пакет (наличие __init__.py) позволяет запускать модули из корня репозитория:
    python -m uvicorn backend.app.main:app --reload
    python -m backend.seed_db
"""
