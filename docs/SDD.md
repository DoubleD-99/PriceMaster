# SOFTWARE DESIGN DOCUMENT (SDD)
**Проект:** Price Master  

## 1. Введение

### 1.1 Назначение документа
Настоящий документ описывает внутреннюю архитектуру, структуру модулей, интерфейсы и алгоритмы системы Price Master. Он предназначен для разработчиков (Настя, Дима, Марина) как руководство по реализации.

**SDD самодостаточен (autonomous).** Он включает в себя нормативные требования ТЗ (`specs_v2.0.docx`) в §10 (Приложение A) и полный план задач по итерациям (`tasks.docx`) в §11 (Приложение B), поэтому для выполнения любой задачи проекта достаточно этого документа.

### 1.2 Область действия
SDD покрывает:
*   Архитектуру Backend (FastAPI) и Frontend (React PWA).
*   Детальную схему БД и стратегии запросов.
*   Механизм работы AI-агента (Tool Calling Loop), все 5 Tools и системный промпт.
*   Внутренние API сервисов и потоки данных.
*   Стратегии безопасности, обработки ошибок и тестирования.
*   Полные требования ТЗ: API, БД, экраны PWA, AI-модуль, безопасность, структура проекта, критерии приёмки (Приложение A).
*   План задач по итерациям и разработчикам (Приложение B).

---

## 2. Общая архитектура системы

### 2.1 Архитектурный стиль
Система использует **Модульную Монолитную Архитектуру** с четким разделением слоев. Это обосновано масштабом проекта (2-3 магазина, малая команда) и позволяет избежать преждевременной сложности микросервисов, сохраняя возможность будущего разделения.

### 2.2 Диаграмма компонентов (C4 Level 2)

Диаграмма вынесена в отдельный файл: **[component_diagram.md](component_diagram.md)**

Всего диаграммы проекта: [context_diagram.md](context_diagram.md) (контекстная), [component_diagram.md](component_diagram.md) (компоненты), [ai_tool_calling_loop.md](ai_tool_calling_loop.md) (цикл AI), [generating_recommendations.md](generating_recommendations.md) (генерация рекомендации), [dfd_mobile_application.md](dfd_mobile_application.md) (потоки PWA), [warehouse_movement.md](warehouse_movement.md) (приёмка/списание), [multistore_context.md](multistore_context.md) (изоляция магазинов).

### 2.3 Ключевые архитектурные решения (ADR)
| ID | Решение | Обоснование | Альтернативы |
| :--- | :--- | :--- | :--- |
| ADR-01 | SQLAlchemy 2.0 Async | Неблокирующий I/O критичен для ожидания ответов LLM (3-5 сек). | Sync ORM (блокирует event loop), Raw SQL (сложная поддержка). |
| ADR-02 | Zustand для стейта | Минимальный бандл, простая интеграция с persist (localStorage). | Redux Toolkit (избыточен), Context API (лишние ре-рендеры). |
| ADR-03 | Tool Calling через Pydantic | Гарантирует типобезопасность аргументов, передаваемых в LLM. | JSON Schema вручную (ошибкоопасно), LangChain (тяжелая зависимость). |
| ADR-04 | Изоляция через Middleware | Единая точка фильтрации по `store_id` исключает утечку данных. | Фильтрация в каждом сервисе (риск человеческого фактора). |

---

## 3. Детальное проектирование Backend

### 3.1 Структура слоев приложения
```text
app/
├── api/              # Только маршрутизация и валидация входных данных
│   ├── deps.py       # Зависимости (get_current_user, get_db, get_store_id)
│   └── v1/           # Версионированные роутеры
├── core/             # Конфигурация, security, exceptions
├── models/           # SQLAlchemy ORM модели (только структура БД)
├── schemas/          # Pydantic схемы (Request/Response/Internal)
├── services/         # Бизнес-логика (НЕ зависит от HTTP)
│   ├── wms.py        # Приемка, списание, проверка партий
│   ├── ai/           # Модуль агента
│   │   ├── agent.py  # Цикл общения с LLM
│   │   ├── tools.py  # Реализация функций для Tools
│   │   └── prompts.py # Шаблоны системных промптов
│   └── analytics.py  # Агрегация данных
└── db/               # Сессия БД, базовый класс
```

### 3.2 Модуль AI-агента (Детализация)

#### 3.2.1 Цикл Tool Calling (Sequence Diagram)
Диаграмма вынесена в отдельный файл: **[ai_tool_calling_loop.md](ai_tool_calling_loop.md)**

#### 3.2.2 Реестр инструментов (Tool Registry Pattern)
Вместо хардкода используется декораторный подход для регистрации инструментов:

```python
# app/services/ai/tools.py
from pydantic import BaseModel, Field


class GetStockLevelArgs(BaseModel):
    product_id: int = Field(description="ID товара")
    store_id: int = Field(description="ID магазина")


@tool(
    name="get_stock_level",
    description="Получает текущие остатки товара с разбивкой по партиям и срокам годности",
    args_schema=GetStockLevelArgs,
)
async def get_stock_level(args: GetStockLevelArgs, db: AsyncSession) -> dict:
    # Реализация запроса к inventory с фильтрацией по expiry_date
    ...
```

#### 3.2.3 Полный набор Tools (5 инструментов)
Все инструменты регистрируются через декоратор `@tool` (см. §3.2.2) и соответствуют ТЗ §7.2:

| Tool | Сигнатура (Pydantic args) | Источник данных / формула |
| :--- | :--- | :--- |
| `get_stock_level` | `{product_id: int, store_id: int}` | `inventory` — остатки с разбивкой по партиям и `expiry_date` |
| `get_sales_trend` | `{product_id: int, store_id: int, days: int}` | агрегация `sales_history` за N дней (среднее, тренд) |
| `check_external_factors` | `{store_id: int, date: str}` | `external_factors` — погода, `is_holiday`, `demand_multiplier` |
| `calculate_reorder_amount` | `{product_id: int, store_id: int}` | средний спрос × срок поставки − текущий остаток (нормируется до кратных упаковок) |
| `calculate_margin_impact` | `{product_id: int, store_id: int, new_price: float}` | см. формулу `expected_impact` в §6.3 |

#### 3.2.4 Системный промпт (ТЗ §7.4)
Хранится в `app/services/ai/prompts.py` и подставляется как `system`-сообщение перед каждым анализом:

> "Ты — аналитик розничной сети Price Master. Твоя цель — максимизировать прибыль и минимизировать списания. Правила: 1. Никогда не вычисляй цены самостоятельно. 2. Для расчетов вызывай Tools. 3. Формируй рекомендацию в формате JSON. 4. Поле reasoning должно быть кратким и понятным."

Триггеры вызова (ТЗ §7.3): кнопка «Анализ» в интерфейсе (`POST /recommendations/generate`) и событийные — `quantity < min_stock`, `expiry_date < 3 дней`.

#### 3.2.5 Безопасность AI-модуля
*   **Whitelist:** LLM может вызывать только функции, зарегистрированные в `ToolRegistry`.
*   **Read-Only для анализа:** Инструменты анализа (`get_*`, `calculate_*`) используют read-only сессию БД.
*   **Write-Operations:** Изменение цены происходит **ТОЛЬКО** через эндпоинт `/accept`, а не напрямую из Tools агента. Агент лишь *предлагает* действие.
*   **Timeout:** Hard limit на выполнение одного tool call — 10 секунд.

Сквозной пример вызова всех Tools при генерации рекомендации: [generating_recommendations.md](generating_recommendations.md)

### 3.3 WMS-логика: Управление партиями (FIFO)
При списании товара (`write-off`) система должна автоматически выбирать старейшую партию:

```sql
-- Логика выбора партии для списания (упрощенно)
SELECT id, quantity FROM inventory 
WHERE product_id = :pid AND store_id = :sid AND quantity > 0
ORDER BY expiry_date ASC, batch_date ASC
LIMIT 1;
```
*Если запрашиваемое количество превышает остаток в одной партии, сервис должен рекурсивно или циклично списывать из следующих партий в рамках одной транзакции.*

Sequence-диаграмма приёмки и списания: [warehouse_movement.md](warehouse_movement.md)

### 3.4 Мультитенантность и безопасность
*   **Middleware:** `TenantMiddleware` извлекает `store_id` из заголовка `X-Store-ID` и токена. Если они не совпадают → 403 Forbidden.
*   **Dependency Injection:** Все сервисы получают `store_id` через зависимость, что делает невозможным случайный доступ к чужим данным.
*   **JWT Payload:** `{ "sub": user_id, "store_ids": [1, 2], "exp": ... }`. Токен содержит список *разрешенных* магазинов.

Sequence-диаграмма изоляции данных по магазинам: [multistore_context.md](multistore_context.md)

---

## 4. Детальное проектирование Frontend (PWA)

### 4.1 Управление состоянием (Zustand Stores)
| Store | Ответственность | Persistence |
| :--- | :--- | :--- |
| `useAuthStore` | Token, User Info, Login/Logout | SessionStorage |
| `useStoreContext` | Текущий `store_id`, список доступных точек | LocalStorage |
| `useScannerStore` | Состояние камеры, последний скан, редирект | Нет |
| `useRecommendations` | Кэш списка рекомендаций, статус принятия | Нет (SWR/React Query) |

### 4.2 Интеграция сканера штрихкодов
*   **Абстракция:** Создать хук `useBarcodeScanner(onDetect: (code: string) => void)`.
*   **Обработка ошибок:** Камера может быть недоступна. Хук должен возвращать `{ isSupported, error, start, stop }`.
*   **Debouncing:** После успешного скана блокировать повторные срабатывания на 2 секунды.
*   **Fallback:** Если камера не поддерживается, показывать поле ручного ввода.

Диаграмма пользовательских потоков PWA (авторизация → сканер → WMS → рекомендации): [dfd_mobile_application.md](dfd_mobile_application.md)

### 4.3 Offline-стратегия (Service Worker)
*   **Cache First:** Статические ассеты (JS, CSS, Icons).
*   **Network First:** API-запросы. При отсутствии сети показывать заглушку "Нет соединения" или кэшированные данные (для справочников).
*   **Manifest:** Обязательные поля `display: standalone`, `theme_color`, `icons` (192x192, 512x512).

---

## 5. Проектирование базы данных (Детали реализации)

### 5.1 Индексы (Критично для производительности)
На основе задач Итерации 3 (Приложение B, B.3, Настя — индексы):
```sql
CREATE INDEX idx_inventory_store_product_expiry ON inventory(store_id, product_id, expiry_date);
CREATE INDEX idx_sales_history_store_date ON sales_history(store_id, sale_date DESC);
CREATE INDEX idx_price_recommendations_status ON price_recommendations(store_id, status, created_at DESC);
CREATE UNIQUE INDEX idx_barcodes_code ON barcodes(code);
```

### 5.2 Триггеры / Проверки целостности
*   **CHECK constraint:** `inventory.quantity >= 0` (защита от отрицательных остатков на уровне БД).
*   **FK Constraints:** `ON DELETE RESTRICT` для `products` и `stores` (нельзя удалить товар, если есть история продаж).

---

## 6. Интерфейсы и контракты

### 6.1 Внутренний контракт AI-рекомендации
Агент ДОЛЕН вернуть JSON, соответствующий этой схеме. Парсер в `agent.py` валидирует ответ через Pydantic:

```python
class AIRecommendationResponse(BaseModel):
    action_type: Literal["price_change", "reorder", "write_off"]
    recommended_value: float
    reasoning: str = Field(max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    expected_impact: float
    tool_calls_used: list[str]  # Для аудита
```

### 6.2 Формат ошибок API
Единый стандарт для всех эндпоинтов:
```json
{
  "error_code": "WMS_INSUFFICIENT_STOCK",
  "message": "Недостаточно товара в партии №123",
  "details": {
    "requested": 10,
    "available": 5,
    "batch_id": 123
  }
}
```

### 6.3 Расчёт ожидаемого эффекта (expected_impact)
Поле `expected_impact` в ответе агента считается **только** Python-функцией (никогда — самой LLM) по формуле из ТЗ §8:

```
expected_impact = (new_price - base_cost) * forecast_sales - current_profit
```

где `base_cost` — себестоимость из `products`, `forecast_sales` — прогноз объёма продаж (`get_sales_trend` × `demand_multiplier` из `external_factors`), `current_profit` — текущая прибыль при действующей цене. Вычисляет `calculate_margin_impact` (§3.2.3), в JSON рекомендации попадает готовое число.

---

## 7. Стратегия тестирования

### 7.1 Unit-тесты (pytest)
*   **AI Tools:** Тестирование математических функций (`calculate_margin_impact`) с фиксированными входными данными. **БЕЗ моков LLM.**
*   **WMS Service:** Тестирование логики FIFO-списания с использованием in-memory SQLite или testcontainers.
*   **Парсер AI:** Подача битых JSON, неполных ответов, галлюцинаций → проверка выброса `ValidationError`.

### 7.2 Integration-тесты (httpx + TestClient)
*   Полный цикл: Авторизация → Выбор магазина → Приемка → Генерация рекомендации → Принятие.
*   Проверка изоляции: Запрос с `store_id=2` и токеном от `store_id=1` должен вернуть 403.

### 7.3 E2E / Ручное тестирование
*   Сценарий "Золотой путь" (Приложение B, B.3, Марина — «Золотой сценарий» демо).
*   Тестирование PWA на реальных устройствах (iOS Safari, Android Chrome).
*   Проверка offline-режима (отключение сети в DevTools).

---

## 8. Развертывание и инфраструктура

### 8.1 Docker Compose (Production-like)
```yaml
services:
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/pricemaster
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      
  db:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
```

### 8.2 Переменные окружения (Security)
*   `.env` **НИКОГДА** не коммитится.
*   `ACCESS_KEY` используется ТОЛЬКО для первичной выдачи JWT. В продакшене рекомендуется заменить на OAuth2 или нормальную регистрацию.
*   `LLM_API_KEY` хранится в секретах (Docker Secrets / Vault / Env vars), не в коде.

---

## 9. Риски и их митигация

| Риск | Вероятность | Влияние | Митигация |
| :--- | :--- | :--- | :--- |
| LLM возвращает невалидный JSON | Высокая | Среднее | Retry logic (до 3 попыток), строгий Pydantic-парсер, fallback-сообщение пользователю. |
| Медленный ответ AI (5+ сек) | Средняя | Высокое | Skeleton screens на фронте, streaming response (опционально), кэширование повторяющихся запросов. |
| Утечка данных между магазинами | Низкая | Критическое | Middleware-изоляция, интеграционные тесты на cross-tenant access, code review всех SQL-запросов. |
| Камера не работает в PWA | Средняя | Среднее | Fallback на ручной ввод ШК, проверка `navigator.mediaDevices` при инициализации. |

---

## 10. Приложение A. Нормативные требования ТЗ (specs_v2.0)

Полная сводка требований Технического Задания. Нормативен в случае расхождений с основной частью SDD.

### A.1 Цель проекта
Price Master — система агентного динамического ценообразования и складского учёта для малого ритейла (сеть 2–3 магазина):
1. Упрощённая WMS-система складского учёта с партиями и сроками годности.
2. AI-агент на базе LLM (Qwen) — анализ данных и рекомендации по ценам и закупкам.
3. Единое адаптивное веб-приложение (PWA) для мобильных устройств и ПК.
4. Интеграция сканера штрихкодов через браузер (html5-qrcode).

Задачи: мультитенантная БД (`store_id`), Backend (FastAPI), AI-агент (Tool Calling), клиент (React + Vite, Mobile-first), Docker Compose, базовая безопасность (токены).

### A.2 Зоны ответственности разработчиков
| Разработчик | Роль | Зона ответственности |
| :--- | :--- | :--- |
| Настя (1) | Backend & DB Architect | PostgreSQL, SQLAlchemy, Alembic, CRUD, WMS-логика, seed-скрипты |
| Дима (2) | AI Engineer & Logic | LLM API integration, Python-tools, промпт-инжиниринг, расчёт маржи и ROI |
| Марина (3) | Frontend & Mobile | React + Vite PWA, адаптивная верстка, html5-qrcode, Recharts |

### A.3 Итерационный план
Три итерации по 2 недели (нед. 1–6): фундамент + склад → AI + PWA → аналитика + демо. Цели, состав задач и разработчики — §11 (Приложение B).

### A.4 Технологический стек
| Компонент | Технология | Обоснование |
| :--- | :--- | :--- |
| Backend | FastAPI + SQLAlchemy 2.0 + Pydantic v2 | Async, типизация, производительность |
| Database | PostgreSQL 15+ | Надёжность, JSONB |
| Migrations | Alembic | Версионирование схемы |
| LLM | Qwen (External OpenAI-compatible API) | Нет GPU на VPS, масштабируемость |
| Web Client | React + Vite + TypeScript (PWA) | Единая кодовая база для ПК и Mobile |
| Scanner | html5-qrcode | Камера браузера без нативных сборок |
| Charts | Recharts | Простая визуализация |
| Deploy | Docker Compose | Простота развёртывания |
| Testing | pytest + httpx | Базовое тестирование API |

### A.5 Спецификация API
Все эндпоинты требуют заголовок `Authorization: Bearer <Token>` и/или `X-Store-ID` для изоляции данных.

**Аутентификация**
*   `POST /auth/login` — Body `{ access_key: str }` → Response `{ token, user_info }`

**Магазины**
*   `GET /stores` — список доступных магазинов

**Товары и Склад (WMS)**
*   `GET /products` — список товаров
*   `GET /inventory` — текущие остатки (фильтр по `store_id`)
*   `POST /wms/receiving` — приёмка; Body `{ product_id, quantity, batch_date, expiry_date }`
*   `POST /wms/write-off` — списание; Body `{ product_id, quantity, reason }`
*   `GET /barcodes/{code}` — поиск товара по штрихкоду

**AI и рекомендации**
*   `POST /recommendations/generate` — запуск анализа агентом
*   `GET /recommendations` — список рекомендаций
*   `POST /recommendations/{id}/accept` — принять рекомендацию (обновляет цену)

**Аналитика**
*   `GET /analytics/sales` — история продаж для графиков

### A.6 Модуль складского учёта
1.  **Приёмка:** запись о поступлении с привязкой к партии (`batch_date`, `expiry_date`), обновление остатков.
2.  **Списание:** фиксация убытков (порча, истечение срока) с указанием причины.
3.  **Партии и сроки годности:** учёт остатков с разбивкой по партиям; алёрты за N дней до истечения.
4.  **Минимальные остатки:** пороги `min_stock` на уровне `product_id + store_id`.
5.  **Штрихкоды:** поиск по ШК через API, сканирование через камеру в PWA.

### A.7 Мульти-магазинность
1.  2–3 магазина, таблица `stores`; у каждого магазина свои остатки и цены.
2.  Общий каталог `products`; все транзакционные таблицы содержат `store_id` (inventory, sales_history, price_history, price_recommendations).
3.  Выбор магазина — выпадающий список в шапке; пользователь видит только данные выбранного магазина (реализация §3.4, §4.1; экран — §A.10).

### A.8 AI-модуль
1.  Роль — аналитик-консультант; LLM **не** выполняет арифметику самостоятельно — все вычисления делегируются Tools (§3.2.3), whitelist инструментов — §3.2.5.
2.  Системный промпт, триггеры вызова и JSON-валидация ответа — §3.2.4, §6.1.

### A.9 Расчёт ожидаемого эффекта
Обязательное поле `expected_impact` рекомендации; формула и методика — §6.3.

### A.10 Экраны приложения (PWA)
1.  **Auth** — ввод Access Key.
2.  **Store Selector** — выбор магазина.
3.  **Dashboard Home** — KPI дня, топ-3 рекомендации, алёрты по срокам годности.
4.  **Recommendations List** — список с кнопками «Принять»/«Отклонить».
5.  **Product Card** — цена, остатки по партиям, история цен, график продаж.
6.  **Scanner** — камера; при успешном скане — переход в карточку товара или форму приёмки.
7.  **Stock Operations** — формы приёмки и списания.
8.  **Analytics** — графики истории цен и продаж.

Требования: единый React + Vite, Mobile-first, PWA manifest (добавление на главный экран).

### A.11 Безопасность и контроль доступа
1.  `ACCESS_KEY` в `.env` — первичный вход; выдаётся простой JWT (без refresh-токенов); хранение токена — §4.1.
2.  Middleware и фильтрация по `store_id` — §3.4; работа с секретами — §8.2.

### A.12 Схема базы данных (SQLAlchemy 2.0, 9 таблиц)
Все транзакционные таблицы содержат `store_id`.

**stores** — id (SERIAL PK), name, address, city (для погодных данных).

**products** — id (PK), name, category, base_cost (DECIMAL), shelf_life_days (INT), min_stock (INT).

**store_products** — id (PK), product_id (FK), store_id (FK), current_price (DECIMAL), is_active (BOOLEAN).

**barcodes** — id (PK), product_id (FK), code (VARCHAR UNIQUE).

**inventory** — id (PK), product_id (FK), store_id (FK), quantity (INT), batch_date (DATE), expiry_date (DATE).

**sales_history** — id (PK), product_id (FK), store_id (FK), quantity_sold (INT), sale_price (DECIMAL), sale_date (TIMESTAMPTZ).

**price_history** — id (PK), product_id (FK), store_id (FK), old_price, new_price, changed_at (TIMESTAMPTZ), recommendation_id (FK nullable).

**external_factors** — id (PK), store_id (FK), date (DATE), weather_condition, is_holiday (BOOLEAN), demand_multiplier (DECIMAL).

**price_recommendations** — id (PK), product_id (FK), store_id (FK), action_type, recommended_value (DECIMAL), reasoning (TEXT), confidence (FLOAT 0..1), status (ожидает/принята/отклонена), expected_impact (DECIMAL), created_at (TIMESTAMPTZ).

### A.13 Структура проекта
```
PriceMaster/
├── backend/                # FastAPI + SQLAlchemy; внутренняя структура app/ — §3.1
│   ├── app/
│   ├── alembic/            # Миграции БД
│   ├── tests/
│   ├── seed_db.py
│   └── Dockerfile
├── web/                    # React PWA (Vite + TS)
│   ├── src/                # screens/, components/, services/, hooks/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── infra/                  # docker-compose.yml, .env.example
└── .github/workflows/      # CI/CD
```

### A.14 Переменные окружения
1.  `DATABASE_URL` — `postgresql+asyncpg://user:pass@db:5432/pricemaster`
2.  `LLM_API_URL` — адрес внешнего API
3.  `LLM_API_KEY` — ключ внешнего API
4.  `JWT_SECRET_KEY` — секрет подписи токенов
5.  `ACCESS_KEY` — мастер-ключ первой регистрации

### A.15 Критерии приёмки
**Итерация 1:** создание 2–3 магазинов; приёмка и списание через API; консистентный seed-скрипт.
**Итерация 2:** рекомендация с JSON-валидацией и обоснованием; адаптивность PWA; сканер ШК через камеру; принятие/отклонение рекомендации в интерфейсе.
**Итерация 3:** дашборд с таблицей рекомендаций и графиками; демо-стенд через Docker Compose; работа с мобильного устройства и ПК.

---

## 11. Приложение B. План задач по итерациям (tasks.docx)

### B.1 Итерация 1: Фундамент + Упрощённый склад (недели 1–2)
**Цель:** инфраструктура, БД, базовый WMS, скелет клиентского приложения.

**Настя — Инициализация и БД:**
*   Развернуть проект FastAPI, настроить структуру папок (api, core, models, schemas, services).
*   Спроектировать все SQLAlchemy 2.0 модели (9 таблиц из ТЗ — §A.12; constraints — §5.2).
*   Настроить Alembic, создать и применить первичную миграцию.

**Настя — Безопасность и API:**
*   Базовая аутентификация (проверка `ACCESS_KEY` из `.env`, выдача JWT).
*   Middleware для проверки токена и заголовка `X-Store-ID`.

**Настя — WMS и CRUD:**
*   CRUD справочников (products, stores, barcodes).
*   `POST /wms/receiving` (создание партии, обновление остатков) и `POST /wms/write-off` (списание с причиной).

**Настя — Инфраструктура:**
*   `docker-compose.yml` (PostgreSQL 15 + FastAPI).
*   `seed_db.py`: синтетические данные (2–3 магазина, каталог, остатки партиями) — §A.13.

**Дима — Архитектура AI и Tools:**
*   Изучить OpenAI-compatible API (Qwen), выбрать библиотеку (litellm / openai python sdk).
*   Спроектировать Tool Calling: перехват запросов LLM → выполнение Python-функций → возврат модели (§3.2.1).
*   Описать сигнатуры (Pydantic) для 5 инструментов (§3.2.3).

**Дима — Аналитика (подготовка):**
*   Помочь Насте с `seed_db.py`: генераторы истории продаж (`sales_history`) и внешних факторов (`external_factors`).
*   Продумать формулы `calculate_margin_impact` и `calculate_reorder_amount`.

**Марина — Инициализация проекта:**
*   React + Vite + TypeScript, PWA (manifest.json, Service Worker, иконки, мета-теги).
*   Роутинг (React Router) и глобальный стейт (Zustand/Redux) для token и store_id.

**Марина — API Клиент и UI Kit:**
*   Axios/Fetch клиент с интерсепторами (Bearer `<Token>`, `X-Store-ID`).
*   Базовый UI-кит Mobile-first: кнопки, инпуты, карточки, модалки, лоадеры.

**Марина — Экраны-заглушки:**
*   Auth (ввод Access Key), Store Selector (выпадающий список).

### B.2 Итерация 2: AI-агент + PWA (недели 3–4)
**Цель:** связать фронтенд с бэкендом, внедрить AI-агента, сканер ШК и основные сценарии UI.

**Настя:**
*   Сервисы чтения данных для Tools Димы (остатки по партиям, агрегация продаж за N дней).
*   `POST /recommendations/generate`; `GET /recommendations`; `POST /recommendations/{id}/accept` (обновление цены в `store_products` + запись в `price_history`) — §6.1, §A.5.
*   `GET /barcodes/{code}`; фоновая задача/вьюха для алёртов (`quantity < min_stock`, `expiry_date < 3 дней`) — §A.6; реализация: SQL-вьюха или background task.

**Дима:**
*   Интеграция Qwen API в FastAPI; системный промпт §3.2.4; парсер и валидатор JSON-ответов LLM.
*   Цикл Tool Calling: LLM → Python Tool → результат в LLM → финальный ответ; математика в Tools (`expected_impact`, закупка, маржа) — §3.2.3, §6.3.
*   Unit-тесты всех Tools pytest'ом (без LLM): граничные значения, формул из ТЗ; тест валидации JSON-схемы ответа агента (битый формат) — §7.1.
*   Тестирование агента на синтетических данных `seed_db.py`, добиться адекватного `reasoning`.

**Марина:**
*   Формы приёмки и списания с выбором партии; html5-qrcode: экран Scanner, доступ к камере, обработка скана, редирект в карточку/форму приёмки — §4.2.
*   Dashboard Home (KPI, топ-3 рекомендации, алёрты по срокам); Recommendations List с кнопками «Принять»/«Отклонить» — §A.10.
*   Адаптивность на реальных устройствах (iOS Safari, Android Chrome); offline-fallback (кэш статики SW); скелетоны при загрузке ответа AI (3–5 сек); глобальный Error Boundary и Toasts (401, 403, 500); сохранение store_id и JWT в LocalStorage — §4.3, §9.

### B.3 Итерация 3: Аналитика + Полировка + Демо (недели 5–6)
**Цель:** визуализация, граничные случаи, оптимизация, демо-стенд и документация.

**Настя:**
*   `GET /analytics/sales` (агрегация); индексы на store_id, product_id, sale_date, batch_date — §5.1, §A.5.
*   Кастомные Exception handlers; production-like Docker Compose (.env, volumes, healthchecks); pytest для WMS-эндпоинтов; CI/CD (ruff/flake8 + pytest при push в main); кастомизация OpenAPI/Swagger (описания, примеры, теги).

**Дима:**
*   Доработка промптов по багам 2-й итерации (агент сам считает цены вместо Tools) — §3.2.4.
*   Edge cases: товара нет в наличии, пустая история продаж, экстремальный внешний фактор — §9.
*   Проверка `expected_impact` по формуле §6.3.
*   Документация архитектуры AI-модуля и списка Tools для защиты проекта.

**Марина:**
*   Recharts; экран Product Card (цена, остатки по партиям, график истории цен, линейный график продаж); тепловая карта / бар-чарт продаж на дашборде — §A.10.
*   Финальная проверка адаптивности, offline-фолбэка, скелетонов.
*   «Золотой сценарий» демо: сканирование → приёмка → алёрт → совет AI → принятие → график.
