# PriceMaster

**Система агентного динамического ценообразования и складского учёта для малого ритейла.**

LLM-агент анализирует остатки, продажи и внешние факторы (погода, праздники),
формирует рекомендации по ценам, пополнению склада и списаниям. Клиент —
mobile-first PWA: сканирование штрихкодов, приёмка и списание, работа с
рекомендациями. Расчёты выполняет Python, LLM — только выбирает действие и
объясняет решение.

## Стек

| Слой | Технология | Почему |
|---|---|---|
| Язык | Python 3.11 | быстрый старт, экосистема ТЗ |
| Backend | FastAPI + SQLAlchemy 2.0 (async) | async, автодокументация `/docs` |
| БД | PostgreSQL 16 | decimal, `TIMESTAMPTZ`, JSON |
| Миграции | Alembic | версионирование схемы |
| LLM | внешний OpenAI-совместимый API | нет GPU на VPS, смена модели через env |
| Клиент | React + Vite + TypeScript (PWA) | единая кодовая база для ПК и мобилок |
| Сканер | html5-qrcode | камера браузера без нативных сборок |
| Инфраструктура | Docker Compose (db, api, web) | воспроизводимый запуск |
| Тесты | pytest (+ httpx), `tsc -b`, `oxlint` | unit по расчётам, integration по API |

## Быстрый старт

### Всё сразу — Docker

```bash
cp .env.example .env   # заполнить секреты
make dc-up             # docker compose up --build
```

API — http://localhost:8000 (`/docs`), PWA — http://localhost:8080.
Остановка — Ctrl+C; `make dc-down`; полный сброс БД — `docker compose down -v`.

### Локально: БД в Docker, API и фронт из исходников

```bash
python -m venv .venv
cp .env.example .env
make install
make db
make seed
make api        # терминал 1, http://127.0.0.1:8000
make web-install
make web        # терминал 2, http://localhost:5173, proxy /api
```

Нужны Python 3.11+, Node.js 20+, Docker и `make` (Windows: Chocolatey, WSL или Git Bash).

## Команды

```bash
make help             # список целей
make install          # зависимости backend
make db               # только PostgreSQL в Docker
make db-down          # остановить PostgreSQL (данные сохраняются)
make seed             # синтетические данные
make api              # FastAPI локально :8000
make test             # pytest
make web-install      # npm install в web/
make web              # Vite :5173
make web-build        # сборка web/dist
make dc-up            # все сервисы Docker
make dc-down          # остановить Docker-сервисы
```

Линт и формат: `ruff check .`, `ruff format --check .`. CI — `.github/workflows/ci.yml`.

## Документация

| Документ | Содержание |
|---|---|
| .env.example | Переменные окружения и секреты |
| docs/SDD.md | проектные контракты, алгоритмы, тестирование |
| docs/agents.md | роль LLM-агента, tools, JSON-контракт, лимиты |
| docs/project-decision.md | принятые решения и обоснования (ADR) |
| docs/TODO.md | план итераций и открытый бэклог |
| docs/BUGS.md | известные дефекты |
