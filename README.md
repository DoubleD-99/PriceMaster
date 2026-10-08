# PriceMaster

**Система агентного динамического ценообразования для малого ритейла.**

LLM-агент (Qwen) анализирует остатки, продажи и внешние факторы (погода,
праздники), формирует рекомендации по изменению цен и пополнению склада.
Клиент — mobile-first PWA: сканирование штрихкодов, приёмка/списание,
принятие рекомендаций в один тап.

**Источник истины — [`docs/SDD.md`](docs/SDD.md)** (разделы 1–9 — дизайн,
Приложение A — ТЗ, Приложение B — план задач). Спека LLM-агента —
[`docs/agents.md`](docs/agents.md). Описание архитектуры и диаграммы — в
`docs/`.

---

## 1. Стек и обоснование

| Слой | Технология | Почему |
|---|---|---|
| Язык | Python 3.11 | быстрый старт, всё из ТЗ на нём |
| Backend | FastAPI + SQLAlchemy 2.0 | async, автодокументация (/docs) |
| БД | PostgreSQL 16 | JSON/децимейлы, TIMESTAMPTZ (ТЗ) |
| Миграции | Alembic | версионирование схемы (SDD, A.13) |
| LLM | Qwen (внешний OpenAI-совместимый API) | нет GPU на VPS, масштабируемость (SDD, A.4) |
| Клиент | React + Vite + TypeScript (PWA) | единая кодовая база для ПК и мобилок (SDD, A.4) |
| Сканер | html5-qrcode | камера браузера без нативных сборок |
| Инфраструктура | Docker Compose (db, api) | простота развёртывания |
| Тесты | pytest (+ httpx) | unit по расчётам, integration по API |

> **LLM не считает цены сам**: все расчёты выполняют Python-функции
> (`backend/app/services/calculations.py`), LLM только выбирает цель и пишет
> обоснование — см. [`docs/agents.md`](docs/agents.md), правило 2.

---

## 2. Структура репозитория

```
PriceMaster/
├── backend/                      # FastAPI + SQLAlchemy (SDD, раздел 3.1)
│   ├── app/
│   │   ├── main.py               # приложение, подключение роутеров api/v1
│   │   ├── api/
│   │   │   ├── deps.py           # JWT, X-Store-ID, сессия БД
│   │   │   └── v1/               # роутеры по SDD, A.5 (auth, stores, products,
│   │   │                         #  inventory, wms, barcodes, recommendations, analytics)
│   │   ├── core/config.py        # настройки из окружения
│   │   ├── db/session.py         # engine, сессия, Base
│   │   ├── models/               # 9 таблиц (SDD, A.12)
│   │   ├── schemas/              # Pydantic-схемы запросов/ответов
│   │   └── services/
│   │       ├── wms.py            # приёмка, списание (FIFO), алёрты
│   │       ├── analytics.py      # агрегация продаж
│   │       ├── calculations.py   # маржинальность, цены, reorder (общие с агентом)
│   │       ├── external_factors.py, synthetic_data.py  # синтетика для seed
│   │       └── ai/               # LLM-агент: agent, tools, prompts
│   ├── alembic/                  # миграции (см. alembic/README.md)
│   ├── seed_db.py                # заполнение БД на 3–6 месяцев
│   └── Dockerfile
├── web/                          # React PWA (заглушка, см. web/README.md)
├── tests/                        # unit/ + integration/ (заглушки под SDD)
├── docs/                         # SDD.md, agents.md, диаграммы
├── requirements.txt              # зависимости рантайма
├── requirements-dev.txt          # зависимости тестов
├── Makefile                      # быстрый локальный запуск
├── docker-compose.yml            # db, api
└── .env.example                  # шаблон секретов
```

---

## 3. Зоны ответственности

| Разработчик | Роль | Модуль |
|---|---|---|
| 1 | Backend & DB Architect | 9 таблиц, Alembic, эндпоинты A.5, `seed_db.py`, WMS |
| 2 | AI Engineer & Logic | `docs/agents.md`, `services/ai/`, `calculations.py`, промпты |
| 3 | Frontend & DevOps | React PWA (`web/`), Docker Compose, VPS, тесты |

---

## 4. Модель данных

9 таблиц (SDD, Приложение A, раздел 12): `stores`, `products`, `barcodes`,
`store_products`, `inventory`, `sales_history`, `price_history`,
`external_factors`, `price_recommendations`. Все транзакционные таблицы
содержат `store_id` (изоляция магазинов).

---

## 5. Функциональность

- **REST API (SDD, A.5):** `POST /auth/login`, `GET /stores`, `GET /products`,
  `GET /inventory`, `POST /wms/receiving`, `POST /wms/write-off`,
  `GET /barcodes/{code}`, `POST /recommendations/generate`,
  `GET /recommendations`, `POST /recommendations/{id}/accept`,
  `GET /analytics/sales`. Все приватные запросы — `Authorization: Bearer <JWT>`
  + `X-Store-ID`.
- **LLM-агент:** 5 tools (SDD, 3.2.3); LLM не производит вычисления —
  только принимает решение и обосновывает текстом. Запуск анализа —
  кнопка «Анализ» (`POST /recommendations/generate`).
- **PWA (web/):** 8 экранов, сканер ШК (html5-qrcode), графики (Recharts) —
  SDD, Приложение A, раздел 10.

---

## 6. Быстрый старт

### 6.1 Всё сразу — Docker (db + api)

```bash
make dc-up     # docker compose up --build: поднимает db + api вместе
```

Остановка: **Ctrl+C** (данные в volume сохраняются); полностью: `make dc-down`.
Полный сброс БД (вместе с томами): `docker compose down -v` (осторожно).

БД отдельно: `make db` (`docker compose up -d db`); только API:
`docker compose up api` — под это нет make-таргета, рекомендуется локальный запуск
(раздел 6.2).

### 6.2 По отдельности — локально (БД в Docker, API из venv)

Терминал 1 — PostgreSQL и данные:

```bash
make db        # поднять только БД на :5432
```

Терминал 2 — API:

```bash
make api       # FastAPI на http://127.0.0.1:8000, документация /docs
```

Остановка — **Ctrl+C** в том же терминале; `make db-down` гасит только контейнер БД (данные сохраняются).

### 6.3 С нуля (полный чеклист локально)

```bash
python -m venv .venv
make install
cp .env.example .env   # заполнить секреты
make db                # терминал 1: PostgreSQL
make seed              # терминал 1: синтетические данные
make api               # терминал 2: API
```

Команды: `make help`, `make test`, `make dc-up`, `make dc-down`.

---

## 7. Запуск в Docker (compose)

`make dc-up` поднимает `db` (PostgreSQL :5432) и `api` (FastAPI :8000) вместе;
переменные берутся из `.env`. Разбор всех способов — раздел 6.

---

## 8. Тесты

```bash
make test
```

- **Unit:** расчёт маржинальности, reorder, внешние факторы
  (`tests/unit/`).
- **Integration:** эндпоинты A.5 и цепочка «API → агент» с замоканным LLM
  (`tests/integration/`).

CI (`.github/workflows/ci.yml`): `ruff check`, `ruff format --check`, `pytest`.

---

## 9. Деплой на VPS

1. `git clone` репозитория, установка Docker/Compose.
2. Заполнить `.env` (`DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_KEY`, `LLM_API_URL`, `LLM_API_KEY`).
3. `docker compose up --build -d`.
4. API — на 8000; открыть доступ через reverse proxy (Caddy/Nginx) при необходимости.