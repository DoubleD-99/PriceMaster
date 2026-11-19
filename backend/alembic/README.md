# Alembic — миграции БД

Каталог для миграций (`backend/alembic/`). Схема БД — docs/requirements.md §4.

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
