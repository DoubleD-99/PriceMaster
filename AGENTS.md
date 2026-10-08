# AGENTS.md — инструкции для кодинг-агента

> Этот файл предназначен для AI-агента, который пишет и меняет **код** в репозитории.
> Спека LLM-агента, который считает рекомендации по ценам, — `docs/agents.md`.

---

## 1. Перед выполнением задачи

1. **Прочитать `docs/SDD.md`** — основной документ проекта:
   * §1–§9 — архитектура, AI-модуль, контракты API, тестирование, деплой;
   * §10 (Приложение A) — полные требования ТЗ (эндпоинты, схема БД, экраны, env);
   * §11 (Приложение B) — план задач по итерациям и разработчикам.
2. Свериться с `README.md` — он описывает **фактическое** состояние репозитория.
3. Если SDD и текущий код расходятся — не переписывать код молча, а показать расхождение пользователю.

> Сейчас код — структурные заглушки под SDD (докстринги, без реализации).
> Реализация ведётся по `docs/SDD.md`, Приложение B (план задач по итерациям).

## 2. Структура репозитория

* `backend/` — FastAPI (структура — SDD, §3.1):
  `app/api/` (deps, `v1/` — роутеры по §A.5), `app/core/`, `app/db/`,
  `app/models/` (9 таблиц — §A.12), `app/schemas/`, `app/services/`
  (wms, analytics, calculations, `ai/` — LLM-агент),
  `alembic/`, `seed_db.py`
* `web/` — React PWA (заглушка, SDD §4/§A.10)
* `tests/` — `unit/` и `integration/`
* `docs/` — SDD, диаграммы, спека LLM-агента (`docs/agents.md`)
* `Makefile`, `docker-compose.yml`, `requirements*.txt`, `.env.example`

## 3. Команды

```bash
make install          # зависимости (runtime + dev)
make db               # только PostgreSQL в Docker
make seed             # заполнить БД синтетическими данными
make api              # FastAPI локально :8000 (--reload)
make test             # pytest (unit + integration)
make dc-up / dc-down  # все сервисы Docker (db, api)

ruff check .          # линт (CI)
ruff format --check . # формат (CI)
```

Python — из `.venv` (Makefile подставляет сам). CI: `.github/workflows/ci.yml`.

## 4. Правила

*   **`.env` никогда не коммитится и не читается в ответах** — только `.env.example`.
*   **Числа для рекомендаций** считаются только в `backend/app/services/calculations.py` — LLM арифметику не выполняет (см. `docs/agents.md`, правило 2). Не переносить расчёты в промпты/код агента.
*   **Ветки:** PR в `main` — только из `dev` (проверяется CI `source-is-develop.yml`).
*   Соблюдать стиль: `ruff check` и `ruff format` должны проходить до коммита.
*   Коммит, push, PR — только по явной просьбе пользователя.
*   Новые зависимости — только в `requirements.txt` / `requirements-dev.txt`.
