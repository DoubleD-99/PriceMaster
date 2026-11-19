import axios from 'axios'

import type {
  InventoryAlerts,
  InventoryItem,
  PriceHistoryEntry,
  Product,
  ProductPrice,
  ReceivingRequest,
  ReceivingResult,
  Recommendation,
  RecommendationGenerateRequest,
  RecommendationStatus,
  SalesAnalytics,
  SalesAnalyticsParams,
  Store,
  TokenResponse,
  WriteOffRequest,
  WriteOffResult,
} from '../types/api'
import { api } from './client'
import { mockApi } from './mock'

const USE_MOCK = import.meta.env.VITE_API_MOCK === 'true'

export { USE_MOCK }

export async function login(accessKey: string): Promise<TokenResponse> {
  if (USE_MOCK) return mockApi.login()
  const { data } = await api.post<TokenResponse>('/auth/login', { access_key: accessKey })
  return data
}

export async function listStores(): Promise<Store[]> {
  if (USE_MOCK) return mockApi.listStores()
  const { data } = await api.get<Store[]>('/stores')
  return data
}

export async function listProducts(): Promise<Product[]> {
  if (USE_MOCK) return mockApi.listProducts()
  const { data } = await api.get<Product[]>('/products')
  return data
}

export async function getProductPrice(productId: number): Promise<ProductPrice | null> {
  if (USE_MOCK) return mockApi.getProductPrice(productId)
  try {
    const { data } = await api.get<ProductPrice>(`/products/${productId}/price`)
    return data
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) return null
    throw err
  }
}

export async function getPriceHistory(productId: number): Promise<PriceHistoryEntry[]> {
  if (USE_MOCK) return mockApi.getPriceHistory(productId)
  const { data } = await api.get<PriceHistoryEntry[]>(`/products/${productId}/price-history`)
  return data
}

export async function listInventory(productId?: number): Promise<InventoryItem[]> {
  if (USE_MOCK) return mockApi.listInventory(productId)
  const { data } = await api.get<InventoryItem[]>('/inventory', {
    params: productId === undefined ? undefined : { product_id: productId },
  })
  return data
}

export async function lookupBarcode(code: string): Promise<Product> {
  if (USE_MOCK) return mockApi.lookupBarcode(code)
  const { data } = await api.get<Product>(`/barcodes/${encodeURIComponent(code)}`)
  return data
}

export async function createReceiving(body: ReceivingRequest): Promise<ReceivingResult> {
  if (USE_MOCK) return mockApi.createReceiving(body)
  const { data } = await api.post<ReceivingResult>('/wms/receiving', body)
  return data
}

export async function createWriteOff(body: WriteOffRequest): Promise<WriteOffResult> {
  if (USE_MOCK) return mockApi.createWriteOff(body)
  const { data } = await api.post<WriteOffResult>('/wms/write-off', body)
  return data
}

export async function getSalesAnalytics(params: SalesAnalyticsParams = {}): Promise<SalesAnalytics> {
  if (USE_MOCK) return mockApi.getSalesAnalytics(params)
  const { data } = await api.get<SalesAnalytics>('/analytics/sales', { params })
  return data
}

export async function getInventoryAlerts(): Promise<InventoryAlerts> {
  if (USE_MOCK) return mockApi.getInventoryAlerts()
  const { data } = await api.get<InventoryAlerts>('/inventory/alerts')
  return data
}

export async function listRecommendations(
  status?: RecommendationStatus,
): Promise<Recommendation[]> {
  if (USE_MOCK) return mockApi.listRecommendations(status)
  const { data } = await api.get<Recommendation[]>('/recommendations', {
    params: status === undefined ? undefined : { status },
  })
  return data
}

export async function generateRecommendations(
  body: RecommendationGenerateRequest = {},
): Promise<Recommendation[]> {
  if (USE_MOCK) return mockApi.generateRecommendations(body)
  const { data } = await api.post<Recommendation[]>('/recommendations/generate', body)
  return data
}

export async function acceptRecommendation(id: number): Promise<Recommendation> {
  if (USE_MOCK) return mockApi.acceptRecommendation(id)
  const { data } = await api.post<Recommendation>(`/recommendations/${id}/accept`)
  return data
}

export async function rejectRecommendation(id: number): Promise<Recommendation> {
  if (USE_MOCK) return mockApi.rejectRecommendation(id)
  const { data } = await api.post<Recommendation>(`/recommendations/${id}/reject`)
  return data
}

export async function checkHealth(): Promise<boolean> {
  if (USE_MOCK) return true
  try {
    await api.get('/health')
    return true
  } catch {
    return false
  }
}
