"""Подключение к базе данных (SQLAlchemy 2.0).

Создаются:
- engine — на основе DATABASE_URL (core/config);
- SessionLocal — фабрика сессий для роутеров, сервисов и seed_db;
- Base — базовый класс DeclarativeBase для всех ORM-моделей (models/).

Миграции схемы — Alembic (backend/alembic/, SDD, Приложение A, раздел 13).
"""
