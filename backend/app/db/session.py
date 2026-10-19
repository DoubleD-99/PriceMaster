"""Подключение к базе данных (SQLAlchemy 2.0).

Создаются:
- engine — на основе DATABASE_URL (core/config);
- SessionLocal — фабрика сессий для роутеров, сервисов и seed_db;
- Base — базовый класс DeclarativeBase для всех ORM-моделей (models/).

Миграции схемы — Alembic (backend/alembic/, SDD, Приложение A, раздел 13).
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
