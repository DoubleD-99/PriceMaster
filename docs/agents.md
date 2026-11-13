# Спецификация LLM-агента

> Поведенческий контракт агента: роль, инструменты, формат ответа, лимиты и
> жизненный цикл рекомендации. Нормативные требования — `docs/requirements.md`,
> проектные контракты — `docs/SDD.md` §3.2, обоснования — `docs/project-decision.md`.
> Промпты строятся на основе этого файла.

---

## 1. Роль агента

Агент — аналитик-советник владельца небольшой розничной сети. На основании
данных БД он формирует рекомендации:

- **снизить цену** — товар с истекающим сроком годности, чтобы избежать списания;
- **повысить цену** — высокий спрос или низкий остаток;
- **пополнить склад** — рассчитанный объём закупки;
- **списать** — порча или истечение срока.

Агент объясняет решение, но не принимает его за владельца: рекомендация
сохраняется со статусом `pending` и ждёт `accept`/`reject`.

---

## 2. Критическое правило: никакой арифметики в LLM

**LLM не вычисляет цены, маржу, скидки, объёмы и `expected_impact`.**

Все числа считаются Python-функциями в `backend/app/services/calculations.py`
и передаются агенту через tools. LLM выбирает инструмент, получает готовый
результат и пишет только `reasoning`.

Это обеспечивает:

- корректность (нет «галлюцинаций арифметики»);
- воспроизводимость и покрытие unit-тестами;
- прозрачность: в рекомендации лежит число из Python, а не из модели.

---

## 3. Инструменты (Tools)

Реестр — `backend/app/services/ai/tools.py`, декоратор `@tool`. Только
зарегистрированные инструменты попадают в whitelist и передаются LLM.
Все инструменты **read-only**, принимают `store_id` и фильтруют данные по
магазину. Аргументы описаны Pydantic-моделями (ADR-03).

| Tool | Аргументы | Возвращает |
|---|---|---|
| `get_stock_level` | `product_id`, `store_id` | `total_quantity`, `batches[]` (`quantity`, `batch_date`, `expiry_date`, `days_to_expiry`), `min_days_to_expiry` |
| `get_sales_trend` | `product_id`, `store_id`, `days=30` | `total_sold`, `avg_daily_sales`, `trend` (`rising`/`falling`/`flat`/`no_data`), `change_pct` |
| `check_external_factors` | `store_id`, `date` (`YYYY-MM-DD`) | `weather_condition`, `is_holiday`, `demand_multiplier`, `available` |
| `calculate_reorder_amount` | `product_id`, `store_id` | `reorder_amount`, `current_stock`, `min_stock`, `avg_daily_sales`, `lead_time_days` |
| `calculate_margin_impact` | `product_id`, `store_id`, `new_price` | `base_cost`, `current_price`, `new_price`, `forecast_sales`, `demand_multiplier`, `expected_impact` |

Ошибки инструментов возвращаются словарём `{error_code, message}` и попадают
в контекст LLM: `TOOL_NOT_ALLOWED`, `TOOL_BAD_ARGUMENTS`, `TOOL_TIMEOUT`,
`PRODUCT_NOT_FOUND`, `PRICE_NOT_FOUND`, `BAD_DATE`.

---

## 4. Формат ответа агента

Финальный ответ — строгий JSON, валидируемый
`AIRecommendationResponse` (`backend/app/schemas/ai.py`, SDD §6.1):

```json
{
  "action_type": "price_change",
  "recommended_value": 149.9,
  "reasoning": "Товар с истекающим сроком годности, спрос падает. Снижение цены уменьшит риск списания.",
  "confidence": 0.82,
  "expected_impact": -320.5,
  "tool_calls_used": [
    "get_stock_level",
    "get_sales_trend",
    "calculate_margin_impact"
  ]
}
```

Правила:

| Поле | Требование |
|---|---|
| `action_type` | `price_change` \| `reorder` \| `write_off` |
| `recommended_value` | новая цена, объём закупки или объём списания из tools |
| `reasoning` | русский язык, 2–3 предложения, ≤ 500 символов; товар, причина, действие |
| `confidence` | `0.0..1.0` |
| `expected_impact` | только из `calculate_margin_impact` |
| `tool_calls_used` | заполняется парсером фактическими вызовами, не памятью LLM |

Парсер `parse_recommendation` терпим к markdown-обёртке ```` ```json ````.
Битый JSON или невалидные поля запускают repair-retry: модели отправляется
ошибка валидации и требование вернуть только JSON.

---

## 5. Цикл Tool Calling

Диаграмма: `docs/diagrams/ai_tool_calling_loop.md`.

1. Системный промпт + user-сообщение о товаре → LLM с whitelist tools.
2. Если LLM вернула `tool_calls`, инструменты выполняются через `call_tool`.
3. Результаты добавляются в историю сообщений как `role: tool`.
4. Цикл повторяется до финального текстового ответа.
5. Ответ парсится и валидируется; при ошибке — до 3 repair-попыток.
6. `tool_calls_used` перезаписывается фактическим списком вызовов.

Лимиты: `MAX_TOOL_ITERATIONS = 5`, `TOOL_TIMEOUT_SECONDS = 10`,
`MAX_REPAIR_ATTEMPTS = 3`. Превышение итераций — `RuntimeError`; таймаут
инструмента — `TOOL_TIMEOUT` в результате.

---

## 6. Жизненный цикл рекомендации

1. **Триггер.** Кнопка «Анализ» (`POST /recommendations/generate`) или событие
   `quantity < min_stock`, `expiry_date < 3 дней`.
2. **Кандидаты.** Pipeline отбирает товары: истекающий срок → скидка;
   высокий спрос/низкий остаток → наценка; остаток меньше спроса на срок
   поставки → закупка; порча → списание.
3. **Анализ.** Для каждого кандидата агент вызывает tools и получает готовые
   числа.
4. **Сохранение.** Рекомендация пишется в `price_recommendations` со статусом
   `pending`.
5. **Решение владельца.**
   - `accept`: для `price_change` обновляется цена в `store_products` и
     создаётся запись в `price_history` с `recommendation_id`; для `reorder` и
     `write_off` меняется только статус (D-08).
   - `reject`: статус `rejected` без изменения цены (D-09).
6. **Повторный анализ.** Учёт отклонённых рекомендаций, чтобы не предлагать
   ту же форму повторно, — **план**, сейчас не реализован (см. `docs/TODO.md`).

---

## 7. Текущее состояние и план

**Реализовано:**

- 5 инструментов и реестр с whitelist;
- цикл tool calling и repair-retry в `agent.py`;
- Pydantic-схема ответа и парсер;
- unit-тесты инструментов, расчётов и цикла агента.

**Не реализовано (итерация 2):**

- подключение `analyze_product` к `POST /recommendations/generate`;
- pipeline выбора кандидатов;
- `GET /recommendations`, `accept`, `reject` — сейчас заглушки;
- учёт отклонённых рекомендаций;
- интеграционный тест «API → агент» с моком LLM (B-04).

---

## 8. Тесты

- `tests/unit/test_ai_tools.py` — аргументы, whitelist, timeout, ошибки данных.
- `tests/unit/test_calculations.py` — формулы и округление.
- `tests/unit/test_agent.py` — цикл, парсер, repair-retry, мок LLM.
- Интеграционный сценарий «API → агент» — план, задача B-04.
