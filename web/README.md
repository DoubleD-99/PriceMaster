# web/ — PWA клиент

Mobile-first PWA на React + Vite + TypeScript.

## Стек

- React 19 + TypeScript, сборка — Vite.
- Роутинг — React Router; состояние — Zustand: токен в памяти/`sessionStorage`,
  `store_id` в `localStorage` (SDD §4.1).
- HTTP — axios с интерсепторами `Authorization: Bearer` и `X-Store-ID`.
- PWA — `vite-plugin-pwa`: manifest, service worker, кэш статики (SDD §4.3).
- Графики — Recharts; сканер — `html5-qrcode`.

## Запуск

Из корня репозитория:

```bash
make web-install   # npm install (один раз)
make web           # dev-сервер http://localhost:5173
make web-build     # прод-сборка в web/dist
```

Либо в `web/`: `npm install`, `npm run dev`, `npm run build`, `npm run lint`,
`npm test`.

## Взаимодействие с API

API-пути идут без общего префикса: `/auth`, `/stores`, `/products`,
`/inventory`, `/wms`, `/barcodes`, `/recommendations`, `/analytics`.
В dev Vite проксирует их на `http://localhost:8000`; в Docker — nginx
(`nginx.conf`). Один origin, CORS не нужен.

Цель прокси переопределяется `VITE_API_TARGET` в `web/.env` (см.
`.env.example`); браузер по-прежнему обращается к тому же origin.

Для параллельной работы без backend: `VITE_API_MOCK=true` — функции из
`src/api/endpoints.ts` отдают данные из `src/api/mock.ts`, включая сценарий
приёмка → списание → рекомендация. Контракт запросов и ответов —
`src/types/api.ts` и SDD §6.4–6.5. Денежные поля backend сериализует строками
(`Decimal`), поэтому типы и форматирование живут в `src/utils/format.ts`.

## Тесты и демо-сценарий

`npm test` проверяет `storeContext` и interceptors axios; `npm run lint` и
`npm run build` — обязательные гейты перед PR.

«Золотой сценарий» демо: выбрать магазин → «Сканер ШК» (или ручной ввод) →
карточка товара → «Приёмка» → «Анализ агентом» на дашборде → «Принять» в списке
рекомендаций → «Аналитика» с графиком продаж. При истекающем сроке алёрт
появляется на дашборде до запуска анализа.

## Структура

```text
src/
├── api/client.ts        axios + интерсепторы Bearer / X-Store-ID
├── api/endpoints.ts     типизированные вызовы API + mock-режим
├── api/mock.ts          фикстуры каталога, склада, рекомендаций и аналитики
├── stores/              Zustand: authStore, storeContext, networkStore
├── hooks/               useNetworkStatus (health-пинг и онлайн-статус)
├── screens/             экраны приложения, включая Product Card и Analytics
├── components/          общие компоненты и навигация
├── utils/               форматирование, названия товаров, подписи рекомендаций
├── types/api.ts         типы запросов/ответов backend
├── App.tsx              роутинг + guard RequireAuth/RequireStore
└── main.tsx
```
