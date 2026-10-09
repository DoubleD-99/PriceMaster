# web/ — PWA клиент (React + Vite + TypeScript)

Mobile-first PWA (SDD, раздел 4; Приложение A, разделы 4 и 10).

## Стек

- React 19 + TypeScript, сборка — Vite
- Роутинг — React Router; стейт — Zustand (token в `sessionStorage`,
  `store_id` в `localStorage`, SDD §4.1)
- HTTP — axios с интерсепторами (`Authorization: Bearer`, `X-Store-ID`)
- PWA — `vite-plugin-pwa` (manifest, service worker, offline-статика, §4.3)

## Запуск

Из корня репозитория:

```bash
make web-install   # npm install (один раз)
make web           # dev-сервер http://localhost:5173
make web-build     # прод-сборка в web/dist
```

Либо напрямую в `web/`: `npm install`, `npm run dev`, `npm run build`.

## Взаимодействие с API

API-пути ТЗ (SDD, A.5) идут без общего префикса (`/auth`, `/stores`,
`/products`, `/inventory`, `/wms`, `/barcodes`, `/recommendations`,
`/analytics`). В dev Vite проксирует их на `http://localhost:8000`
(бэкенд поднимается через `make api`) — единый origin, CORS не нужен.
Переопределить цель прокси можно переменной `VITE_API_TARGET`.

В проде то же делает nginx внутри контейнера `web` — см. `nginx.conf`.

## Структура

```
src/
├── api/client.ts        # axios + интерсепторы Bearer / X-Store-ID
├── stores/              # Zustand: authStore, storeContext
├── screens/             # Auth, Store Selector, Dashboard (заглушки)
├── App.tsx              # роутинг + guard RequireAuth
└── main.tsx
```

Экраны и функциональность развиваются по итерациям (SDD, Приложение B).
