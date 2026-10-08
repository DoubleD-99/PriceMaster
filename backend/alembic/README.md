# Alembic — миграции БД

Каталог для миграций по SDD, Приложение A, раздел 13 (`backend/alembic/`).

Инициализация (один раз, из `backend/`):

```bash
alembic init alembic
```

Затем настроить `alembic.ini` и `alembic/env.py` под `DATABASE_URL`
из `.env` (SQLAlchemy URL, `sqlalchemy.url` — из окружения) и создать
первую ревизию:

```bash
alembic revision --autogenerate -m "initial schema (9 tables)"
alembic upgrade head
```

Схема БД (9 таблиц) — SDD, Приложение A, раздел 12.
