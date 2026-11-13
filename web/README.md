# web/ — PWA клиент

Mobile-first PWA на React + Vite + TypeScript. Контракты — [`../docs/SDD.md`](../docs/SDD.md)
§4, требования к экранам — [`../docs/requirements.md`](../docs/requirements.md) §2.4.

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

## Структура

```text
src/
├── api/client.ts        axios + интерсепторы Bearer / X-Store-ID
├── stores/              Zustand: authStore, storeContext
├── screens/             экраны приложения
├── components/          общие компоненты и навигация
├── types/api.ts         типы ответов backend
├── App.tsx              роутинг + guard RequireAuth
└── main.tsx
```

Правила и команды репозитория — [`../AGENTS.md`](../AGENTS.md); текущий план —
[`../docs/TODO.md`](../docs/TODO.md).
