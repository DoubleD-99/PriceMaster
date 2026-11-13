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

Либо в `web/`: `npm install`, `npm run dev`, `npm run build`, `npm run lint`.

## Взаимодействие с API

API-пути идут без общего префикса: `/auth`, `/stores`, `/products`,
`/inventory`, `/wms`, `/barcodes`, `/recommendations`, `/analytics`.
В dev Vite проксирует их на `http://localhost:8000`; в Docker — nginx
(`nginx.conf`). Один origin, CORS не нужен.

Цель прокси переопределяется `VITE_API_TARGET` в `web/.env` (см.
`.env.example`); браузер по-прежнему обращается к тому же origin.

Для параллельной работы без backend: `VITE_API_MOCK=true` — функции из
`src/api/endpoints.ts` отдают данные из `src/api/mock.ts`. Контракт запросов
и ответов — `src/types/api.ts` и SDD §6.4–6.5.

## Структура

```text
src/
├── api/client.ts        axios + интерсепторы Bearer / X-Store-ID
├── api/endpoints.ts     типизированные вызовы API + mock-режим
├── api/mock.ts          фикстуры рекомендаций и алертов
├── stores/              Zustand: authStore, storeContext
├── screens/             экраны приложения
├── components/          общие компоненты и навигация
├── types/api.ts         типы запросов/ответов backend
├── App.tsx              роутинг + guard RequireAuth
└── main.tsx
```
