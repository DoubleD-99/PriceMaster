import type {
  InventoryAlerts,
  Recommendation,
  RecommendationGenerateRequest,
  RecommendationStatus,
} from '../types/api'

const now = new Date().toISOString()

let recommendations: Recommendation[] = [
  {
    id: 1,
    product_id: 1,
    store_id: 1,
    action_type: 'price_change',
    recommended_value: 89.9,
    reasoning: 'Срок годности истекает через 2 дня, спрос падает. Снижение цены уменьшит риск списания.',
    confidence: 0.82,
    status: 'pending',
    expected_impact: -320.5,
    created_at: now,
  },
  {
    id: 2,
    product_id: 2,
    store_id: 1,
    action_type: 'reorder',
    recommended_value: 24,
    reasoning: 'Остаток ниже минимального, спрос стабильный. Нужно пополнить склад.',
    confidence: 0.74,
    status: 'pending',
    expected_impact: 540,
    created_at: now,
  },
]

const alerts: InventoryAlerts = {
  expiring_soon: [
    { product_id: 1, batch_id: 10, expiry_date: '2026-11-15', days_left: 2 },
  ],
  low_stock: [{ product_id: 2, quantity: 4, min_stock: 5 }],
}

export const mockApi = {
  async listRecommendations(status?: RecommendationStatus): Promise<Recommendation[]> {
    if (status === undefined) return [...recommendations]
    return recommendations.filter((row) => row.status === status)
  },

  async generateRecommendations(
    body: RecommendationGenerateRequest = {},
  ): Promise<Recommendation[]> {
    const productId = body.product_id ?? 1
    const created: Recommendation = {
      id: recommendations.length + 1,
      product_id: productId,
      store_id: 1,
      action_type: 'price_change',
      recommended_value: 99.9,
      reasoning: 'Демо-рекомендация из mock-режима. Реальные данные появятся после подключения API.',
      confidence: 0.7,
      status: 'pending',
      expected_impact: 120,
      created_at: new Date().toISOString(),
    }
    recommendations = [created, ...recommendations]
    return [created]
  },

  async acceptRecommendation(id: number): Promise<Recommendation> {
    return updateStatus(id, 'accepted')
  },

  async rejectRecommendation(id: number): Promise<Recommendation> {
    return updateStatus(id, 'rejected')
  },

  async getInventoryAlerts(): Promise<InventoryAlerts> {
    return alerts
  },
}

function updateStatus(id: number, status: RecommendationStatus): Recommendation {
  const found = recommendations.find((row) => row.id === id)
  if (found === undefined) throw new Error(`Рекомендация id=${id} не найдена`)
  if (found.status !== 'pending') throw new Error('Рекомендация уже обработана')
  found.status = status
  return found
}
