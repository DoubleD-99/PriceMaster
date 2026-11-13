import axios from 'axios'

import { useAuthStore } from '../stores/authStore'
import { useStoreContext } from '../stores/storeContext'

// baseURL пустой — запросы идут на тот же origin, который в dev проксирует
// Vite, а в проде — nginx (single-origin, без CORS, D-11).
export const api = axios.create({
  baseURL: '',
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
