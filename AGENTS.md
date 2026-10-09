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
*   Новые зависимости — только в `requirements.txt` / `requirements-dev.txt`.

### 4.1 Ветки и коммиты

Модель ветвления (проверяется CI, `.github/workflows/`):
*   `main` — релизная ветка; **прямые коммиты и push в неё запрещены**.
*   `dev` — интеграционная; PR в `main` разрешён **только из `dev`** (`source-is-develop.yml`).
*   Фича-ветки создаются **от `dev`** и вливаются обратно в `dev` коротким PR.
    Прямые коммиты в `dev` — только для тривиальных правок, не пересекающихся с другими.

Имена веток: `<type>/<short-desc>` — латиница, kebab-case, нижний регистр.
`<type>`: `feature`, `fix`, `hotfix`, `chore`, `docs`, `refactor`.
Примеры текущей итерации: `feature/backend-core-wms`, `feature/ai-tools-design`, `feature/web-pwa-init`.

Коммиты — **Conventional Commits** (`feat:`, `fix:`, `ci:` ...), сообщение на английском, императив.
Перед коммитом обязательны `ruff check .` и `ruff format --check .`.
Коммит, push, PR — только по явной просьбе пользователя.
