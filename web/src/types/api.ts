export type DecimalString = string

export type UserInfo = {
  user_id: number
  username: string
  store_ids: number[]
}

export type TokenResponse = {
  token: string
  user_info: UserInfo
}

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
  base_cost: DecimalString
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

export type ProductPrice = {
  product_id: number
  store_id: number
  current_price: DecimalString
}

export type PriceHistoryEntry = {
  id: number
  product_id: number
  store_id: number
  old_price: DecimalString
  new_price: DecimalString
  changed_at: string
  recommendation_id: number | null
}

export type ReceivingRequest = {
  product_id: number
  quantity: number
  batch_date: string
  expiry_date: string
}

export type ReceivingResult = {
  batch: InventoryItem
  quantity_added: number
}

export type WriteOffRequest = {
  product_id: number
  quantity: number
  reason: string
}

export type WriteOffBatch = {
  batch_id: number
  expiry_date: string
  quantity: number
}

export type WriteOffResult = {
  product_id: number
  store_id: number
  quantity: number
  reason: string
  batches: WriteOffBatch[]
}

export type RecommendationAction = 'price_change' | 'reorder' | 'write_off'
export type RecommendationStatus = 'pending' | 'accepted' | 'rejected'

export type Recommendation = {
  id: number
  product_id: number
  store_id: number
  action_type: RecommendationAction
  recommended_value: DecimalString
  current_price: DecimalString | null
  current_stock: number | null
  reasoning: string
  confidence: number
  status: RecommendationStatus
  expected_impact: DecimalString
  created_at: string
}

export type RecommendationGenerateRequest = {
  product_id?: number | null
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

export type SalesSummary = {
  total_revenue: DecimalString
  total_quantity: number
  sales_count: number
  average_check: DecimalString
}

export type SalesByDay = {
  date: string
  revenue: DecimalString
  quantity: number
  sales_count: number
  average_check: DecimalString
}

export type SalesByProduct = {
  product_id: number
  revenue: DecimalString
  quantity: number
  sales_count: number
  average_check: DecimalString
}

export type SalesAnalytics = {
  summary: SalesSummary
  by_day: SalesByDay[]
  by_product: SalesByProduct[]
}

export type SalesAnalyticsParams = {
  date_from?: string
  date_to?: string
  product_id?: number
}

export type ErrorResponse = {
  error_code: string
  message: string
  details: Record<string, unknown>
}

export type ApiError = ErrorResponse
