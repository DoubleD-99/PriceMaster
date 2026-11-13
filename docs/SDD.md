# Software Design Document (SDD)

## 1. Введение

### 1.1. Назначение и карта документов

SDD описывает проектные решения, контракты и алгоритмы, которых нет в коде явно.

### 1.2. Область действия

- контракты AI-модуля и расчётов;
- FIFO-логика WMS и изоляция магазинов;
- неочевидные решения фронтенда (хранение токена, сканер, offline);
- индексы и ограничения БД;
- тестирование.

## 2. Общая архитектура

### 2.1. Архитектурный стиль

Модульный монолит; бизнес-логика в `services` не зависит от HTTP.

### 2.2. Диаграммы

- `docs/diagrams/ai_tool_calling_loop.md` — цикл tool calling.
- `docs/diagrams/warehouse_movement.md` — приёмка и списание.
- `docs/diagrams/multistore_context.md` — изоляция магазинов.

## 3. Детальное проектирование Backend

### 3.1. Структура слоёв

Актуальное дерево — `backend/app/`. Правила разделения:

- `api/` — маршрутизация, зависимости, HTTP-ошибки;
- `services/` — бизнес-логика и запросы к БД, без HTTP;
- `models/` — SQLAlchemy-модели, `schemas/` — Pydantic-схемы;
- `core/` — конфигурация и безопасность, `db/` — сессия и `Base`.

### 3.2. Модуль AI-агента

Описан в `docs/agents.md` (роль, инструменты, системный промпт, лимиты, жизненный цикл, безопасность). Контракт ответа `AIRecommendationResponse` — §6.1.

### 3.3. WMS: управление партиями (FIFO)

При списании выбираются партии с наименьшим `expiry_date`, затем `batch_date`:

```sql
SELECT id, quantity FROM inventory
WHERE product_id = :pid AND store_id = :sid AND quantity > 0
ORDER BY expiry_date ASC, batch_date ASC;
```

Списание продолжается по следующим партиям, пока не набрано нужное количество.
Нехватка остатка — ошибка `WMS_INSUFFICIENT_STOCK` в формате §6.2.

### 3.4. Мультитенантность и безопасность

- `TenantMiddleware` проверяет JWT и согласует `X-Store-ID` со списком
  магазинов токена; чужой магазин → 403.
- Все запросы к транзакционным таблицам фильтруются по `store_id`.
- JWT payload: `{ "sub": user_id, "store_ids": [1, 2], "exp": ... }`.

## 4. Детальное проектирование Frontend (PWA)

### 4.1. Управление состоянием

- `useAuthStore` — JWT; сейчас `sessionStorage` (временное решение, см. BUG-06
  и `docs/project-decision.md` D-07).
- `useStoreContext` — выбранный `store_id` в `localStorage`.
- Рекомендации — серверное состояние; не persist в Zustand.

### 4.2. Интеграция сканера штрихкодов

- Сканирование — `html5-qrcode` в браузере.
- После успешного скана — `GET /barcodes/{code}` и переход в карточку/форму.
- Повторные срабатывания блокируются на 2 секунды.
- Если камера недоступна — ручной ввод ШК.

### 4.3. Offline-стратегия

- Статические ассеты — Cache First.
- API — Network First; при отсутствии сети показывать ошибку или кэш справочников.
- Manifest: `display: standalone`, `theme_color`, иконки 192×192 и 512×512.
- Текущее ограничение: кэшируется только статика, баннер offline — в BUG-07.

## 5. База данных: детали реализации

### 5.1. Индексы

Есть:

- `barcodes.code` — уникальный;
- `inventory(store_id)`, `inventory(product_id)`, `inventory(batch_date)`;
- `sales_history(store_id)`, `sales_history(product_id)`, `sales_history(sale_date)`.

Не хватает индексов для `price_history`, `external_factors`,
`price_recommendations` — задача B-12 в `docs/TODO.md`.

### 5.2. Ограничения целостности

- `CHECK (inventory.quantity >= 0)`.
- FK на `products` и `stores` — `ON DELETE RESTRICT`.
- `price_history.recommendation_id` — nullable FK.

## 6. Интерфейсы и контракты

### 6.1. Контракт AI-рекомендации

```python
class AIRecommendationResponse(BaseModel):
    action_type: Literal["price_change", "reorder", "write_off"]
    recommended_value: float
    reasoning: str = Field(max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    expected_impact: float
    tool_calls_used: list[str]
```

Парсер — `services/ai/agent.py`.

### 6.2. Формат ошибок API

```json
{
  "error_code": "WMS_INSUFFICIENT_STOCK",
  "message": "Недостаточно товара в партии №123",
  "details": {"requested": 10, "available": 5, "batch_id": 123}
}
```

WMS-ошибки формируются `services/wms.py`; единый обработчик для остальных
эндпоинтов — задача B-08 в `docs/TODO.md`.

### 6.3. Расчёт ожидаемого эффекта

`expected_impact` считается только Python-функцией
`calculations.margin_impact`:

```text
forecast_sales = avg_daily_sales × demand_multiplier × FORECAST_DAYS
new_profit     = (new_price − base_cost) × forecast_sales
current_profit = (current_price − base_cost) × forecast_sales
expected_impact = new_profit − current_profit
```

`FORECAST_DAYS = 30`, `LEAD_TIME_DAYS = 3`. В рекомендацию попадает готовое
число.

### 6.4. Контракт рекомендаций

| Метод | Путь | Тело / query | Ответ |
|---|---|---|---|
| POST | `/recommendations/generate` | `{product_id?: int, limit?: int}` | `RecommendationOut[]` |
| GET | `/recommendations` | `status?: pending\|accepted\|rejected` | `RecommendationOut[]` |
| POST | `/recommendations/{id}/accept` | — | `RecommendationOut` |
| POST | `/recommendations/{id}/reject` | — | `RecommendationOut` |

`RecommendationOut`: `id`, `product_id`, `store_id`, `action_type`,
`recommended_value`, `reasoning`, `confidence`, `status`, `expected_impact`,
`created_at`. `action_type` — `price_change | reorder | write_off`;
`status` — `pending | accepted | rejected`.

`generate` без `product_id` берёт кандидатов из алертов (истекающий срок,
остаток ниже `min_stock`) и анализирует не больше `limit`. Ошибки — §6.2:
`PRODUCT_NOT_FOUND` 404, `RECOMMENDATION_NOT_FOUND` 404,
`RECOMMENDATION_ALREADY_PROCESSED` 409, `STORE_PRODUCT_NOT_FOUND` 404,
`LLM_NOT_CONFIGURED` 503, `LLM_INVALID_RESPONSE` 502, `LLM_ERROR` 502.

### 6.5. Контракт алертов

`GET /inventory/alerts` возвращает `InventoryAlertsOut`:

```json
{
  "expiring_soon": [
    {"product_id": 1, "batch_id": 10, "expiry_date": "2026-11-15", "days_left": 2}
  ],
  "low_stock": [
    {"product_id": 2, "quantity": 4, "min_stock": 5}
  ]
}
```

Требуется JWT + `X-Store-ID`; данные только выбранного магазина.

## 7. Стратегия тестирования

### 7.1. Unit-тесты

- `tests/unit/test_calculations.py` — формулы маржи, скидки, reorder, `expected_impact`.
- `tests/unit/test_external_factors.py` — погода, праздники, `demand_multiplier`.
- `tests/unit/test_ai_tools.py` — инструменты, whitelist, timeout, ошибки аргументов.
- `tests/unit/test_agent.py` — парсер, tool-loop, repair-retry, мок LLM.
- `tests/unit/test_api_contract.py` — наличие путей и полей контрактов §6.4–6.5.

### 7.2. Integration-тесты

`tests/integration/test_api.py`: авторизация, изоляция магазинов, справочники,
приёмка, списание FIFO, поиск по ШК. `tests/integration/test_recommendations_api.py`:
алерты, generate, list, accept, reject, сквозной сценарий «API → агент» с `mock_llm`.

### 7.3. E2E и ручная проверка

- «Золотой сценарий»: сканирование → приёмка → алёрт → рекомендация → принятие → график.
- Проверка PWA на iOS Safari и Android Chrome.
- Проверка offline-режима в DevTools.

## 8. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| LLM возвращает невалидный JSON | Высокая | Среднее | Repair-retry (3 попытки), строгий Pydantic-парсер |
| Медленный ответ LLM | Средняя | Высокое | Ограничение числа кандидатов, таймауты, скелетоны на фронте |
| Утечка данных между магазинами | Низкая | Критическое | Middleware-изоляция, integration-тесты, фильтрация по `store_id` |
| Камера не работает в PWA | Средняя | Среднее | Ручной ввод ШК как fallback |
| Модель считает числа сама | Средняя | Высокое | Промпт, `expected_impact` только из tools, аудит `tool_calls_used` |
