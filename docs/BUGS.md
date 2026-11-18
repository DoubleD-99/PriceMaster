# Известные дефекты

Только подтверждённые дефекты кода и поведения. Задачи на развитие и
тестовые пробелы — `docs/TODO.md`, обоснования решений —
`docs/project-decision.md`, контракты — `docs/SDD.md`.

**Статусы:** `открыт` — воспроизводится; `в работе` — есть исполнитель;
`исправлен` — закрыт с проверкой.

## Сводка

| ID | Дефект | Приоритет | Статус |
|---|---|---|---|
| BUG-01 | Типы фронтенда не соответствуют backend | P1 | исправлен |
| BUG-02 | `VITE_API_URL` ломает single-origin | P1 | исправлен |
| BUG-03 | Нет эндпоинта алертов | P1 | исправлен |
| BUG-04 | Алёрты теряют товары и имеют неверный тип | P2 | исправлен |
| BUG-05 | Экран выбора магазина недоступен | P2 | исправлен |
| BUG-06 | Истёкший JWT и отсутствие refresh | P1 | открыт |
| BUG-07 | PWA выглядит рабочей без сети | P2 | исправлен |
| BUG-08 | У `web` нет healthcheck | P2 | открыт |
| BUG-09 | Небезопасные дефолты секретов | P1 | открыт |

---

## BUG-01. Типы фронтенда не соответствуют backend

**Где:** `web/src/types/api.ts`.

**Симптом.** Типы `Store`, `Product`, `InventoryItem`, `Recommendation`,
`ApiError` описывают другую схему: `sku`, `barcode`, `brand`, `purchase_price`,
`qty_on_hand`, `reason_code`, статусы `NEW/ACCEPTED/...`. Backend возвращает
`base_cost`, `min_stock`, `quantity`, `batch_date`, `expiry_date`,
`action_type`, `recommended_value`, `reasoning`, `status = pending|accepted|rejected`.

**Влияние.** Экраны нельзя подключить к реальному API без ручных преобразований;
ошибки WMS (`error_code/message/details`) не типизированы.

**Что сделано.** Типы приведены к схемам `backend/app/schemas/`: `StoreOut`,
`ProductOut`, `InventoryOut`, `RecommendationOut`, WMS и аналитика. Денежные
поля (`Decimal`) описаны строками и форматируются на клиенте; объект ошибки —
`{error_code, message, details}`.

---

## BUG-02. `VITE_API_URL` ломает single-origin

**Где:** `web/.env.example`, `web/src/api/client.ts`.

**Симптом.** Пример предлагает `VITE_API_URL=http://localhost:8000`. При
копировании `.env` фронт идёт напрямую на другой origin, а `CORSMiddleware`
не настроен → запросы падают с CORS-ошибкой.

**Влияние.** Локальный запуск по инструкции не работает; ломается D-11
(single-origin).

**Что сделать.** Убрать/опустошить `VITE_API_URL` в примере; для dev
использовать `VITE_API_TARGET` (цель прокси Vite). Либо добавить
`CORSMiddleware` с allowlist, но это противоречит выбранному single-origin.

---

## BUG-03. Нет эндпоинта алертов

**Где:** `backend/app/services/wms.py::alerts`, `backend/app/api/v1/`.

**Симптом.** Сервис `alerts()` считает истекающие партии и остатки ниже
`min_stock`, но роутера нет. `GET /inventory/alerts` отсутствует.

**Влияние.** Dashboard Home не может показать алёрты; решение D-10 не
реализовано.

**Что сделать.** Добавить `GET /inventory/alerts` с `X-Store-ID`, отдавать
результат `wms.alerts()`, покрыть integration-тестом.

---

## BUG-04. Алёрты теряют товары и имеют неверный тип

**Где:** `backend/app/services/wms.py::alerts`.

**Симптом.**
- Аннотация возврата `dict[list[dict]]` неверна, корректно — `dict[str, list[dict]]`.
- `low_stock` строится только по товарам, у которых есть строки в `inventory`.
  Товар с нулевым остатком (нет строк) не попадёт в алёрты, хотя он ниже
  `min_stock`.

**Влияние.** Часть критичных остатков не показывается; статические проверки
типов вводят в заблуждение.

**Что сделать.** Исправить аннотацию; строить `low_stock` по активным товарам
магазина (left join / отдельный запрос), а не только по существующим партиям;
добавить тест на товар без остатков.

---

## BUG-05. Экран выбора магазина недоступен

**Где:** `web/src/App.tsx`, `web/src/screens/StoreSelector.tsx`,
`web/src/components/StoreSelect.tsx`.

**Симптом.** Маршрут `/select-store` открывается только сразу после логина.
Из навигации входа нет; дропдаун в топбаре дублирует выбор магазина.

**Влияние.** Если `storeId` не выбран, приватные запросы уходят без
`X-Store-ID` и получают 400. Пользователь не понимает, как вернуться к выбору.

**Что сделано.** В настройках добавлена кнопка «Сменить магазин»; маршруты
прикладных экранов защищены `RequireStore`, поэтому при `storeId = null`
пользователя переводит на `/select-store` вместо запросов без `X-Store-ID`.

---

## BUG-06. Истёкший JWT и отсутствие refresh

**Где:** `web/src/stores/authStore.ts`, `web/src/api/client.ts`,
`backend/app/api/v1/auth.py`, `backend/app/core/security.py`.

**Симптом.** JWT (HS256, TTL 12 ч) хранится в `sessionStorage`. Refresh-токенов
нет, response-интерсептора нет. После истечения токена приложение молча
ломается: 401 не приводит к выходу на `/login`, `RequireAuth` проверяет только
наличие токена.

**Влияние.** Потеря сессии после закрытия вкладки и при истечении TTL;
пользователь видит непонятные ошибки; известное расхождение с формулировками
о хранении токена.

**Целевая схема.** Access-токен (TTL 15 мин) — только в памяти JS;
refresh-токен (TTL 30 дней) — cookie `HttpOnly; SameSite=Lax; Path=/auth;
Secure` в проде. Тихий refresh при старте и по 401 (одна попытка, затем повтор
запроса). `POST /auth/logout` очищает cookie.

**Backend.** `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS`, `COOKIE_*`
в конфиге; отдельный refresh-JWT с claim `type=refresh`; `POST /auth/refresh`,
`POST /auth/logout`; публичные пути в middleware.

**Frontend.** Токен в памяти, `userInfo`; response-интерсептор 401 → refresh →
повтор; boot-состояние с тихим refresh; «Выйти» вызывает `/auth/logout`.

**Риски.** `Secure` требует HTTPS в проде; `withCredentials` и CORS; stateless
refresh нельзя отозвать без таблицы сессий; после F5 нужен тихий refresh.

**Тесты.** Refresh без cookie → 401; валидная cookie → новый access; refresh-JWT
не принимается как `Bearer`; logout удаляет cookie; TTL.

---

## BUG-07. PWA выглядит рабочей без сети

**Где:** service worker (`web/vite.config.ts`), `web/src/screens/AuthScreen.tsx`.

**Симптом.** Service worker кэширует статику, поэтому при выключенном backend
интерфейс рисуется, но API-запросы падают. Баннера «нет связи» нет; на логине
показывается общее «Сервер недоступен».

**Влияние.** На демо выглядит как «приложение живое, но данные не грузятся»;
пользователь не понимает причину.

**Что сделано.** `useNetworkStatus` пингует `GET /health` при старте, фокусе,
событиях online/offline и раз в минуту. При отсутствии связи показывается
баннер, а мутирующие запросы отклоняются интерсептором с внятным сообщением.
`/health` добавлен в прокси Vite и nginx. Service worker в dev отключён
настройкой `vite-plugin-pwa` по умолчанию.

---

## BUG-08. У `web` нет healthcheck

**Где:** `docker-compose.yml`.

**Симптом.** У `db` и `api` healthcheck есть, у `web` — нет; `depends_on`
не отражает готовность API.

**Влияние.** Оркестратор считает `web` готовым раньше, чем API; production-like
compose неполный.

**Что сделано.** Добавлен healthcheck для `web` и `depends_on` на
`api: condition: service_healthy`.

---

## BUG-09. Небезопасные дефолты секретов

**Где:** `backend/app/core/config.py`.

**Симптом.** `JWT_SECRET_KEY` по умолчанию `"FORTUNA812"`, `ACCESS_KEY` —
`"secret"`. Если `.env` не заполнен, приложение стартует с известными секретами.

**Влияние.** Компрометация токенов и входа в прод-окружении.

**Что сделать.** Сделать секреты обязательными (без дефолтов) и падать при
старте, если они не заданы; в `.env.example` оставить только плейсхолдеры.
