import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// Пути API из ТЗ (SDD, A.5) монтируются без общего префикса, поэтому
// в dev проксируем каждый префикс на FastAPI — без CORS и без правок
// фронтенд-кода. В проде то же делают nginx (см. web/nginx.conf).
const API_PREFIXES = [
  'auth',
  'stores',
  'products',
  'inventory',
  'wms',
  'barcodes',
  'recommendations',
  'analytics',
]

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'pwa-icon.svg'],
      manifest: {
        name: 'PriceMaster',
        short_name: 'PriceMaster',
        description: 'Агентное динамическое ценообразование для малого ритейла',
        lang: 'ru',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        theme_color: '#2563eb',
        background_color: '#ffffff',
        icons: [
          {
            src: 'pwa-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any',
          },
          {
            src: 'pwa-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
        navigateFallbackDenylist: [new RegExp(`^/(${API_PREFIXES.join('|')})/`)],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API_PREFIXES.map((prefix) => [
        `/${prefix}`,
        {
          target: process.env.VITE_API_TARGET ?? 'http://localhost:8000',
          changeOrigin: true,
        },
      ]),
    ),
  },
})
