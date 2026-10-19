"""Фикстуры pytest.

- db_schema  (session, autouse) — тестовая БД `<имя>_test`: создаёт её при
  необходимости, пересоздаёт таблицы перед сессией тестов, гасит engine
  после. URL берётся из TEST_DATABASE_URL или DATABASE_URL (.env);
- clean_tables (function, autouse) — очистка таблиц перед каждым тестом,
  чтобы тесты были независимы;
- api_client — httpx.AsyncClient (ASGITransport) против backend.app.main.app;
- auth_client — api_client, залогиненный через POST /auth/login;
- shop — 2 магазина + 2 товара + штрихкоды (минимальные данные WMS);
- mock_llm — заглушка вызова LLM (для интеграционного теста «API → агент»
  без реальной модели, SDD, раздел 6).

Все фикстуры и тесты работают в одном event loop (см. pytest.ini):
engine SQLAlchemy создаёт соединения в нем же — без конфликтов циклов.
"""

import os
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings

# Тестовая БД — отдельная от dev: make test не трогает разработческие данные.
# ВАЖНО: пропатчить settings ДО импорта db.session (engine создаётся при импорте).
if "TEST_DATABASE_URL" in os.environ:
    TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
else:
    _head, _name = settings.DATABASE_URL.rsplit("/", 1)
    TEST_DATABASE_URL = f"{_head}/{_name}_test"
settings.DATABASE_URL = TEST_DATABASE_URL

from backend.app.db.session import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.models import (
    Barcode,
    ExternalFactor,
    Inventory,
    PriceHistory,
    PriceRecommendation,
    Product,
    SalesHistory,
    Store,
    StoreProduct,
)

# Дочерние таблицы — перед родительскими (FK restrict).
DATA_TABLES = [
    PriceHistory,
    PriceRecommendation,
    Inventory,
    SalesHistory,
    ExternalFactor,
    StoreProduct,
    Barcode,
    Product,
    Store,
]


async def _ensure_database_exists(url: str) -> None:
    """CREATE DATABASE <имя>_test, если его ещё нет (через базу postgres)."""
    admin_url, db_name = url.rsplit("/", 1)
    admin = create_async_engine(f"{admin_url}/postgres", isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_schema():
    """Схема тестовой БД: создать БД (если нужно) + create_all на сессию."""
    await _ensure_database_exists(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_schema):
    """Пустые таблицы перед каждым тестом (независимость тестов)."""
    async with SessionLocal() as session:
        for model in DATA_TABLES:
            await session.execute(delete(model))
        await session.commit()
    yield


@pytest_asyncio.fixture
async def api_client():
    """HTTP-клиент против FastAPI-приложения (без реального сервера)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def shop(db_schema) -> dict:
    """Минимальные данные WMS: 2 магазина, 2 товара, штрихкоды."""
    async with SessionLocal() as session:
        stores = [
            Store(name="Тест-магазин А", address="ул. А, 1", city="Москва"),
            Store(name="Тест-магазин Б", address="ул. Б, 2", city="Казань"),
        ]
        session.add_all(stores)
        await session.flush()

        products = [
            Product(
                name="Молоко 3.2%, 900 мл",
                category="Молочные",
                base_cost=65.00,
                shelf_life_days=14,
                min_stock=10,
            ),
            Product(
                name="Хлеб бородинский",
                category="Хлеб",
                base_cost=45.00,
                shelf_life_days=3,
                min_stock=5,
            ),
        ]
        session.add_all(products)
        await session.flush()

        session.add_all(
            [
                Barcode(product_id=products[0].id, code="4600000000001"),
                Barcode(product_id=products[1].id, code="4600000000002"),
            ]
        )
        await session.commit()
        return {
            "store_ids": [s.id for s in stores],
            "product_ids": [p.id for p in products],
        }


@pytest_asyncio.fixture
async def auth_client(api_client, shop) -> httpx.AsyncClient:
    """api_client с валидным JWT (все магазины из shop)."""
    response = await api_client.post(
        "/auth/login", json={"access_key": settings.ACCESS_KEY}
    )
    assert response.status_code == 200, response.text
    api_client.headers["Authorization"] = f"Bearer {response.json()['token']}"
    return api_client


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Заглушка LLM-вызова (OpenAI-совместимый API) — реальный мок появится
    вместе с интеграцией агента в Итерации 2."""
    return AsyncMock()
