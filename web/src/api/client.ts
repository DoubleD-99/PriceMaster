import axios from 'axios'

import { useAuthStore } from '../stores/authStore'
import { useStoreContext } from '../stores/storeContext'

// baseURL по умолчанию пустой — запросы идут на тот же origin, который
// в dev проксирует Vite, а в проде — nginx (single origin, без CORS).
// Можно переопределить через VITE_API_URL (см. web/.env.example).
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const storeId = useStoreContext.getState().storeId
  if (storeId !== null) {
    config.headers['X-Store-ID'] = String(storeId)
  }
  return config
})
