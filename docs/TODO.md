# TODO и план работ

**Правила**

1. Задача попадает в итерацию, только если не блокирует критерии приёмки
   (`docs/requirements.md` §7) и есть ресурс.
2. При завершении: задача → код → тесты → отметка здесь.
3. Осознанные отступления от ТЗ — не долг, а решения; они живут в
   `docs/project-decision.md`, а не в бэклоге.

---

## 1. План по итерациям

### Итерация 1. Фундамент + WMS (недели 1–2)

**Статус:** завершена, кроме write-CRUD справочников (решение D-03).

- [x] FastAPI, структура `api/core/models/schemas/services/db`.
- [x] SQLAlchemy 2.0: 9 таблиц, ограничения.
- [x] Alembic: первичная миграция.
- [x] Аутентификация по `ACCESS_KEY`, выдача JWT.
- [x] `TenantMiddleware`, проверка `X-Store-ID`.
- [x] Чтение справочников: `GET /stores`, `/products`, `/inventory`, `/barcodes/{code}`.
- [x] WMS: `POST /wms/receiving`, `POST /wms/write-off` (FIFO).
- [x] `docker-compose.yml`: db + api.
- [x] `seed_db.py`: магазины, каталог, остатки партиями, продажи, внешние факторы.
- [x] AI: изучен OpenAI-совместимый API, спроектированы 5 tools и схема tool calling.
- [x] PWA: React + Vite + TypeScript, роутинг, Zustand, manifest, service worker.
- [x] API-клиент с `Authorization` и `X-Store-ID`, базовый UI-кит.
- [x] Экраны Auth и Store Selector.

### Итерация 2. AI-агент + PWA (недели 3–4)

**Статус:** завершена.

- [x] AI-модуль: `tools.py`, `agent.py`, `prompts.py`, JSON-валидация.
- [x] Unit-тесты инструментов, расчётов и цикла агента.
- [x] `POST /recommendations/generate` — базовый pipeline + mock-тест.
- [x] `GET /recommendations` — фильтр по статусу, сортировка.
- [x] `POST /recommendations/{id}/accept` — D-08.
- [x] `POST /recommendations/{id}/reject` — D-09.
- [x] Pipeline выбора кандидатов по алертам (базовый).
- [x] `GET /inventory/alerts` — BUG-03/BUG-04.
- [x] Выравнивание `web/src/types/api.ts` под backend — BUG-01.
- [x] Формы приёмки/списания в PWA.
- [x] Интеграция сканера с API и переходом в карточку/форму.
- [x] Dashboard Home и Recommendations List на реальных данных.
- [x] Интеграционный тест «API → агент» с моком LLM — B-04.
- [x] Smoke-тест агента на синтетических данных — `tests/integration/test_agent_smoke.py`.
- [x] Seed намеренно не создаёт рекомендации — они появляются через `generate`.

### Итерация 3. Аналитика + полировка + демо (недели 5–6)

**Статус:** завершена.

- [x] `GET /analytics/sales` и агрегация продаж.
- [x] Индексы для `price_history`, `external_factors`, `price_recommendations` — B-12 (модели + миграция `a7b8c9d0e1f2`).
- [x] Кастомные exception handlers и единый формат ошибок — B-08 (`backend/app/api/errors.py`, обработчики в `main.py`).
- [x] Кастомизация Swagger/OpenAPI — B-09 (теги, summary/description, ответы ошибок).
- [x] Product Card, Analytics, Recharts, графики продаж.
- [x] Финальная проверка адаптивности и offline-фолбэка.
- [x] «Золотой сценарий» демо: сканирование → приёмка → алёрт → рекомендация → принятие → график.

---

## 2. Бэклог

| ID | Задача | Приоритет | Оценка | Статус |
|---|---|---|---|---|
| B-04 | Интеграционный тест «API → агент» с моком LLM | P1 | 0,5 дня | закрыт |
| B-08 | Exception handlers и единый формат ошибок | P2 | 0,5 дня | закрыт |
| B-09 | Кастомизация Swagger/OpenAPI | P2 | 0,5 дня | закрыт |
| B-11 | Makefile: цели для Docker | P3 | 20 мин | открыт |
| B-12 | Индексы для аналитики | P2 | 2 ч + миграция | закрыт |
| B-13 | Автотесты фронтенда | P3 | 1 день | закрыт |
| B-14 | Трейкинг вызовов tools | P3 | 0,5 дня | открыт |
| B-15 | Кандидаты «на подумать» | P3 | — | открыт |
| B-17 | Ссылки на документацию в docstring кода | P3 | 0,5 дня | открыт |
| B-18 | Цена и история цен в Product Card | P2 | 1 день | открыт |
| B-19 | Offline-кэш справочников API | P2 | 1 день | открыт |

### B-04. Интеграционный тест «API → агент»

**Статус:** закрыт. `test_generate_api_to_agent_with_mock_llm` в
`tests/integration/test_recommendations_api.py` прогоняет
`POST /recommendations/generate` через настоящий `analyze_product`, мок LLM
(`mock_llm` в `tests/conftest.py`) и проверяет tool call +
`expected_impact` из Python-расчёта.

### B-08. Exception handlers и единый формат ошибок

**Статус:** закрыт. `backend/app/api/errors.py` + глобальные обработчики в
`backend/app/main.py`; единый формат `{error_code, message, details}`,
`X-Request-ID` и логирование `request_id`.

### B-09. Swagger и OpenAPI

**Статус:** закрыт. Метаданные приложения, теги по разделам, `summary`/`description`,
ответы ошибок на ключевых эндпоинтах; `backend/app/api/openapi.py` приводит
схему к runtime-контракту: `X-Store-ID` обязателен, 400/403/422 используют
`ErrorResponse`.

### B-11. Makefile: цели для Docker

`make dc-up` работает в foreground. Добавить `dc-up-d`, `dc-logs`, `dc-restart`,
`dc-reset` (с предупреждением про `down -v`).

### B-12. Индексы для аналитики

**Статус:** закрыт. Индексы в моделях и миграция Alembic
`a7b8c9d0e1f2_add_analytics_indexes.py`.

### B-13. Тесты фронтенда

**Статус:** закрыт. `npm test` (Vitest + jsdom) проверяет персистентность
`storeContext`, подстановку `Authorization`/`X-Store-ID` и блокировку мутаций
без связи с backend. В `Makefile` добавлены цели `web-test` и `web-lint`.
Playwright-сценарий не реализован: «золотой
сценарий» описан в `web/README.md` и проверяется вручную.

### B-14. Трейкинг вызовов tools

Для демо и защиты показывать, что агент вызвал инструменты и получил готовые
числа. Добавить структурный лог (имя, аргументы, результат, длительность) и
счётчик вызовов в ответ `POST /recommendations/generate`.

### B-15. Кандидаты «на подумать»

Не подтверждены ТЗ, на усмотрение команды:

- Web Push вместо Telegram-бота;
- экспорт рекомендаций в CSV/PDF;
- роли пользователей (владелец/продавец).

### B-17. Ссылки на документацию в docstring

После выделения `requirements.md` и удаления Приложений A/B в docstring кода
остались ссылки на старую структуру SDD. Нужно пройтись по `backend/` и `web/`
и обновить ссылки на актуальные разделы.

### B-18. Цена и история цен в Product Card

`docs/requirements.md` §2.4 требует цену и историю изменений в карточке товара.
Отдельных эндпоинтов нет; сейчас UI показывает последнюю принятую цену из
рекомендаций. Нужны store-scoped `GET /products/{id}/price` и
`GET /products/{id}/price-history`, схемы, web-типы и замена фолбэка в
`web/src/screens/ProductCardScreen.tsx`.

### B-19. Offline-кэш справочников API

`docs/SDD.md` §4.3 описывает API Network First с кэшем справочников; сейчас
кэшируются только статические ассеты, мутации блокированы, показывается баннер.
Нужно кэшировать `/stores`, `/products`, `/barcodes/{code}` с учётом
`X-Store-ID`, TTL и инвалидацией после восстановления связи.

---

## 3. Параллельная работа

Контракты итерации 2 зафиксированы в `docs/SDD.md` §6.4–6.5,
`backend/app/schemas/` и `web/src/types/api.ts`. Менять поля, статусы или коды
ошибок — только одновременно в backend, frontend и контракте.

| Поток | Зона | Файлы | Гейт |
|---|---|---|---|
| Backend API | recommendations, alerts | `api/v1/recommendations.py`, `api/v1/inventory.py`, `services/recommendations.py`, `schemas/` | integration-тесты эндпоинтов |
| Agent | pipeline кандидатов, generate | `services/ai/`, `services/recommendations.py` | B-04 зелёный |
| Frontend | экраны, типы, mock | `web/src/api/`, `web/src/types/api.ts`, `web/src/screens/` | `npm run build`, `npm run lint`, `npm test` |
| Integration | контракт и сквозной сценарий | `tests/`, `docs/SDD.md` §6 | контрактные + integration-тесты зелёные |

- Frontend может работать без backend: `VITE_API_MOCK=true` в `web/.env`.
- Backend может работать без реальной LLM: `mock_llm` в `tests/conftest.py`.
- Ветки — `<type>/<short-desc>` от `dev`; PR не меняет контракт без отметки в
  этом разделе.

---

## 4. Закрытые решения

Решение D-01 (Telegram-бот), D-02 (PWA вместо нативного приложения) и D-03
(read-only справочники) зафиксированы в `docs/project-decision.md`.
В бэклог они не входят; вернуться к ним можно только при пересмотре требований.
