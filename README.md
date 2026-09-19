# PriceMaster

**Система агентного динамического ценообразования для малого ритейла.**

LLM-агент анализирует остатки, продажи и внешние факторы (погода, праздники),
формирует рекомендации по изменению цен и пополнению склада. Общается с владельцем
через Telegram-бота, показывается на веб-дашборде.

---

## 1. Стек и обоснование

| Слой | Технология | Почему |
|---|---|---|
| Язык | Python 3.11 | быстрый старт, универсальность для API/агента/бота, всё из ТЗ на нём |
| Backend | FastAPI + SQLAlchemy 2.0 | async, автодокументация (/docs), ORM по ТЗ |
| БД | PostgreSQL 16 | основной стек по ТЗ, JSON/децимейлы, TIMESTAMPTZ |
| Модель данных | Pydantic v2 + SQLAlchemy 2.0 `DeclarativeBase` | типизация запросов и схем по ТЗ |
| LLM | Qwen (локально через Ollama, любой размер) или любой OpenAI-совместимый API | бесплатный локальный деплой, GDPR-friendly |
| Клиент | Telegram-бот (aiogram 3) + веб-дашборд (FastAPI templates + Chart.js) | бот — основной UI, дашборд — график истории цен |
| Инфраструктура | Docker + docker-compose (db, api, bot, llm) | изоляция, деплой на VPS |
| Тесты | pytest (+pytest-asyncio, httpx) | unit по расчётам, integration по цепочке бот→API→агент |

> **LLM:** Модель выносится в переменную `LLM_MODEL`
> Агент **не считает цены сам**: все расчёты выполняют Python-функции (tools), LLM только
> выбирает цель и пишет текстовое обоснование (см. `agents.md`).

---

## 2. Структура репозитория

```
PriceMaster/
├── backend/                        # модуль данных и API (FastAPI + SQLAlchemy)
│   ├── app/
│   │   ├── main.py                 # создание приложения, подключение роутеров и дашборда
│   │   ├── config.py               # настройки из переменных окружения
│   │   ├── database.py             # engine, сессия, Base (SQLAlchemy 2.0)
│   │   ├── models.py               # 6 таблиц
│   │   │                           # external_factors, price_recommendations
│   │   ├── schemas.py              # Pydantic-схемы запросов/ответов API
│   │   ├── routers/
│   │   │   ├── products.py         # GET /products — товары с остатками
│   │   │   ├── sales.py            # POST /sales — внесение продажи
│   │   │   ├── recommendations.py  # GET /recommendations — советы агента
│   │   │   └── price_history.py    # GET /price-history/{product_id}
│   │   ├── services/
│   │   │   ├── external_factors.py # синтетическая погода/праздники/demand_multiplier
│   │   │   ├── calculations.py     # маржинальность, reorder amount (общие для API и агента)
│   │   │   └── synthetic_data.py   # генерация продаж с сезонностью для seed
│   │   └── templates/dashboard.html# веб-дашборд
│   ├── seed_db.py                  # заполнение БД на 3–6 месяцев
│   └── Dockerfile
├── ai_agent/                # модуль агентной логики
│   ├── tools.py             # тулзы
│   ├── agent.py             # оркестрация
│   ├── prompts.py           # системный промпт для LLM
│   └── Dockerfile
├── bot/                     # модуль клиента
│   ├── main.py              # запуск поллинга, подключение middleware и хендлеров
│   ├── auth.py              # whitelist в памяти + проверка ACCESS_KEY
│   ├── middleware.py        # блокировка неавторизованных пользователей
│   ├── api_client.py        # HTTP-клиент к backend API
│   ├── keyboards.py         # кнопки Принять / Отклонить / Подробнее
│   ├── handlers/
│   │   ├── auth.py          # /start, /auth [password]
│   │   ├── report.py        # /report — топ-3 срочных изменения цен
│   │   ├── stock_report.py  # /stock_report — сводка по закупкам
│   │   ├── daily_summary.py # /daily_summary — выручка, топ-3, динамика
│   │   ├── product.py       # /product [название] — карточка товара
│   │   └── callbacks.py     # обработка нажатий на кнопки
│   └── Dockerfile
├── tests/                   # тестовое окружение
│   ├── conftest.py
│   ├── unit/                # маржинальность, reorder, внешние факторы
│   └── integration/         # эндпоинты API и цепочка бот → API → агент (мок LLM)
├── agents.md                # Spec-Driven Development: спека агента
├── requirements.txt         # зависимости рантайма
├── requirements-dev.txt     # зависимости тестов
├── Makefile                 # быстрый локальный запуск
├── docker-compose.yml       # db, api, bot, llm
└── .env.example             # шаблон секретов
```

---

## 3. Зоны ответственности

| Разработчик | Роль | Модуль |
|---|---|---|
| 1 | Backend & DB Architect | БД, миграции, CRUD-эндпоинты FastAPI, `seed_db.py`, внешние факторы |
| 2 | AI Engineer & Logic | `agents.md`, tools агента, промпты, алгоритмы маржи и закупки |
| 3 | Frontend & DevOps | Telegram-бот, дашборд, Docker-compose, VPS, тесты |

---

## 4. Модель данных
`products`, `inventory`, `sales_history`, `price_history`, `external_factors`,
`price_recommendations` — полное описание колонок в ТЗ (раздел 4) и в `backend/app/models.py`.

---

## 5. Функциональность

- **REST API (FastAPI):** `GET /products`, `POST /sales`, `GET /recommendations`,
  `GET /price-history/{product_id}`, `GET /dashboard` (веб-дашборд).
- **LLM-агент:** 4 инструмента (`get_stock_level`, `get_sales_trend`,
  `check_external_factors`, `calculate_reorder_amount`); LLM не производит вычисления — только
  принимает решение и обосновывает текстом.
- **Telegram-бот (aiogram):** `/auth [password]` — регистрация по `ACCESS_KEY`, whitelist в памяти,
  команды `/report`, `/stock_report`, `/daily_summary`, `/product …` + кнопки принять/отклонить рекомендацию.
- **Веб-дашборд:** FastAPI templates (Jinja2) + Chart.js — график истории цен и таблица рекомендаций.

---

## 6. Быстрый старт (локально, без Docker)

```bash
# 1. Окружение
python -m venv .venv

# 2. Зависимости
make install

# 3. Секреты
cp .env.example .env   # и укажите DATABASE_URL, BOT_TOKEN, ACCESS_KEY

# 4. База PostgreSQL должна быть запущена (см. раздел 7 или свой экземпляр)

# 5. Заполнить БД тестовыми данными (3–6 месяцев продаж + внешние факторы)
make seed

# 6. Запуск
make api     # FastAPI на http://127.0.0.1:8000 (документация: /docs, дашборд: /dashboard)
make bot     # Telegram-bot
make local   # FastAPI + Telegram-bot
```

Команды: `make help`, `make test`, `make dc-up`, `make dc-down`.

---

## 7. Запуск в Docker (compose)

```bash
cp .env.example .env
docker compose up --build
```

Сервисы: `db` (PostgreSQL :5432), `api` (FastAPI :8000), `bot` (Telegram), `llm` (Ollama :11434).

Подтянуть модель LLM:

```bash
docker compose exec llm ollama pull qwen2.5:14b   # или qwen2.5:7b
```

---

## 8. Тесты

```bash
make test
```

- **Unit:** расчёт маржинальности, `calculate_reorder_amount`, генерация внешних факторов.
- **Integration:** эндпоинты API (`/products`, `/sales`, `/recommendations`, `/price-history`),
  цепочка бот → API → агент (LLM замокана).

---

## 9. Деплой на VPS

1. `git clone` репозитория, установка Docker/Compose.
2. Заполнить `.env` (`BOT_TOKEN`, `ACCESS_KEY`, `DATABASE_URL`, `LLM_MODEL`).
3. `docker compose up --build -d`.
4. Дашборд и API — на 8000, бот — работает напрямую в Telegram, LLM — на 11434.
5. Открыть доступ до 8000 через reverse proxy (Caddy/Nginx) при необходимости.