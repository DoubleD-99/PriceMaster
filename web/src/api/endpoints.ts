import type {
  InventoryAlerts,
  Recommendation,
  RecommendationGenerateRequest,
  RecommendationStatus,
} from '../types/api'
import { api } from './client'
import { mockApi } from './mock'

const USE_MOCK = import.meta.env.VITE_API_MOCK === 'true'

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
