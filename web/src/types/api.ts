export type Store = {
  id: number
  name: string
  address: string
  city: string
}

export type Product = {
  id: number
  name: string
  category: string
  base_cost: number
  shelf_life_days: number
  min_stock: number
}

export type InventoryItem = {
  id: number
  product_id: number
  store_id: number
  quantity: number
  batch_date: string
  expiry_date: string
}

export type RecommendationAction = 'price_change' | 'reorder' | 'write_off'
export type RecommendationStatus = 'pending' | 'accepted' | 'rejected'

export type Recommendation = {
  id: number
  product_id: number
  store_id: number
  action_type: RecommendationAction
  recommended_value: number
  reasoning: string
  confidence: number
  status: RecommendationStatus
  expected_impact: number
  created_at: string
}

export type RecommendationGenerateRequest = {
  product_id?: number
  limit?: number
}

export type ExpiringBatchAlert = {
  product_id: number
  batch_id: number
  expiry_date: string
  days_left: number
}

export type LowStockAlert = {
  product_id: number
  quantity: number
  min_stock: number
}

export type InventoryAlerts = {
  expiring_soon: ExpiringBatchAlert[]
  low_stock: LowStockAlert[]
}

export type ErrorResponse = {
  error_code: string
  message: string
  details: Record<string, unknown>
}

export type ApiError = ErrorResponse | { detail: string | Record<string, string[]> }
