import axios from 'axios'

import { useAuthStore } from '../stores/authStore'
import { useNetworkStore } from '../stores/networkStore'
import { useStoreContext } from '../stores/storeContext'

// baseURL пустой — запросы идут на тот же origin, который в dev проксирует
// Vite, а в проде — nginx (single-origin, без CORS, D-11).
export const api = axios.create({
  baseURL: '',
})

api.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase() ?? 'get'
  const isMutation = ['post', 'put', 'patch', 'delete'].includes(method)
  if (
    isMutation &&
    (!navigator.onLine || useNetworkStore.getState().backendOnline === false)
  ) {
    return Promise.reject(new Error('Нет связи с сервером. Изменения не отправлены.'))
  }
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
