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

const isoDate = (date: Date) => date.toISOString().slice(0, 10)
const addDays = (days: number) => {
  const date = new Date()
  date.setUTCDate(date.getUTCDate() + days)
  return isoDate(date)
}

const now = new Date().toISOString()

const stores: Store[] = [
  { id: 1, name: 'Магазин на Ленина', address: 'ул. Ленина, 10', city: 'Москва' },
  { id: 2, name: 'Магазин на Мира', address: 'пр. Мира, 25', city: 'Казань' },
]

const products: Product[] = [
  { id: 1, name: 'Йогурт 1,5%', category: 'Молочное', base_cost: '45.00', shelf_life_days: 7, min_stock: 5 },
  { id: 2, name: 'Хлеб пшеничный', category: 'Выпечка', base_cost: '28.00', shelf_life_days: 3, min_stock: 8 },
  { id: 3, name: 'Кофе в зёрнах', category: 'Бакалея', base_cost: '320.00', shelf_life_days: 180, min_stock: 3 },
]

const prices: ProductPrice[] = [
  { product_id: 1, store_id: 1, current_price: '95.0' },
  { product_id: 2, store_id: 1, current_price: '55.0' },
  { product_id: 3, store_id: 1, current_price: '690.0' },
]

const priceHistory: PriceHistoryEntry[] = [
  { id: 1, product_id: 1, store_id: 1, old_price: '89.0', new_price: '95.0', changed_at: addDays(-10) + 'T10:00:00.000Z', recommendation_id: null },
  { id: 2, product_id: 2, store_id: 1, old_price: '52.0', new_price: '55.0', changed_at: addDays(-5) + 'T10:00:00.000Z', recommendation_id: null },
]

const barcodes: Record<string, number> = {
  '4600000000001': 1,
  '4600000000002': 2,
  '4600000000003': 3,
}

let inventory: InventoryItem[] = [
  { id: 1, product_id: 1, store_id: 1, quantity: 12, batch_date: addDays(-4), expiry_date: addDays(2) },
  { id: 2, product_id: 2, store_id: 1, quantity: 4, batch_date: addDays(-1), expiry_date: addDays(2) },
  { id: 3, product_id: 3, store_id: 1, quantity: 10, batch_date: addDays(-20), expiry_date: addDays(160) },
]

let recommendations: Recommendation[] = [
  {
    id: 1,
    product_id: 1,
    store_id: 1,
    action_type: 'price_change',
    recommended_value: '89.9',
    current_price: '95.0',
    current_stock: 12,
    reasoning: 'Срок годности истекает через 2 дня, спрос падает. Снижение цены уменьшит риск списания.',
    confidence: 0.82,
    status: 'pending',
    expected_impact: '-320.50',
    created_at: now,
  },
  {
    id: 2,
    product_id: 2,
    store_id: 1,
    action_type: 'reorder',
    recommended_value: '24',
    current_price: '55.0',
    current_stock: 4,
    reasoning: 'Остаток ниже минимального, спрос стабильный. Нужно пополнить склад.',
    confidence: 0.74,
    status: 'pending',
    expected_impact: '540.00',
    created_at: now,
  },
]

const alerts: InventoryAlerts = {
  expiring_soon: [
    { product_id: 1, batch_id: 1, expiry_date: addDays(2), days_left: 2 },
    { product_id: 2, batch_id: 2, expiry_date: addDays(2), days_left: 2 },
  ],
  low_stock: [{ product_id: 2, quantity: 4, min_stock: 8 }],
}

const salesAnalytics = (params: SalesAnalyticsParams = {}): SalesAnalytics => {
  const rows = products
    .filter((product) => params.product_id === undefined || product.id === params.product_id)
    .map((product, index) => ({
      product_id: product.id,
      revenue: `${(index + 2) * 450}.00`,
      quantity: (index + 2) * 9,
      sales_count: (index + 2) * 3,
      average_check: '150.00',
    }))
  const totalRevenue = rows.reduce((sum, row) => sum + Number(row.revenue), 0)
  const totalQuantity = rows.reduce((sum, row) => sum + row.quantity, 0)
  const salesCount = rows.reduce((sum, row) => sum + row.sales_count, 0)
  return {
    summary: {
      total_revenue: `${totalRevenue.toFixed(2)}`,
      total_quantity: totalQuantity,
      sales_count: salesCount,
      average_check: salesCount > 0 ? `${(totalRevenue / salesCount).toFixed(2)}` : '0.00',
    },
    by_day: [
      { date: addDays(-2), revenue: '900.00', quantity: 18, sales_count: 6, average_check: '150.00' },
      { date: addDays(-1), revenue: '1350.00', quantity: 27, sales_count: 9, average_check: '150.00' },
      { date: addDays(0), revenue: '1800.00', quantity: 36, sales_count: 12, average_check: '150.00' },
    ],
    by_product: rows,
  }
}

function updateStatus(id: number, status: RecommendationStatus): Recommendation {
  const found = recommendations.find((row) => row.id === id)
  if (found === undefined) throw new Error(`Рекомендация id=${id} не найдена`)
  if (found.status !== 'pending') throw new Error('Рекомендация уже обработана')
  found.status = status
  return found
}

export const mockApi = {
  async login(): Promise<TokenResponse> {
    return {
      token: 'mock-token',
      user_info: { user_id: 1, username: 'admin', store_ids: stores.map((store) => store.id) },
    }
  },

  async listStores(): Promise<Store[]> {
    return [...stores]
  },

  async listProducts(): Promise<Product[]> {
    return [...products]
  },

  async listInventory(productId?: number): Promise<InventoryItem[]> {
    return inventory.filter((row) => productId === undefined || row.product_id === productId)
  },

  async lookupBarcode(code: string): Promise<Product> {
    const productId = barcodes[code]
    const found = products.find((product) => product.id === productId)
    if (found === undefined) throw new Error(`Штрих-код ${code} не найден`)
    return found
  },

  async getProductPrice(productId: number): Promise<ProductPrice | null> {
    return prices.find((row) => row.product_id === productId) ?? null
  },

  async getPriceHistory(productId: number): Promise<PriceHistoryEntry[]> {
    return priceHistory.filter((row) => row.product_id === productId)
  },

  async createReceiving(body: ReceivingRequest): Promise<ReceivingResult> {
    const found = inventory.find(
      (row) =>
        row.store_id === 1 &&
        row.product_id === body.product_id &&
        row.batch_date === body.batch_date &&
        row.expiry_date === body.expiry_date,
    )
    if (found) {
      found.quantity += body.quantity
      return { batch: { ...found }, quantity_added: body.quantity }
    }
    const batch: InventoryItem = {
      id: Math.max(0, ...inventory.map((row) => row.id)) + 1,
      store_id: 1,
      product_id: body.product_id,
      quantity: body.quantity,
      batch_date: body.batch_date,
      expiry_date: body.expiry_date,
    }
    inventory = [...inventory, batch]
    return { batch: { ...batch }, quantity_added: body.quantity }
  },

  async createWriteOff(body: WriteOffRequest): Promise<WriteOffResult> {
    const candidates = inventory
      .filter((row) => row.store_id === 1 && row.product_id === body.product_id && row.quantity > 0)
      .sort((a, b) => a.expiry_date.localeCompare(b.expiry_date))
    const available = candidates.reduce((sum, row) => sum + row.quantity, 0)
    if (available < body.quantity) throw new Error('Недостаточно товара для списания')
    let remaining = body.quantity
    const batches = candidates
      .map((row) => {
        const quantity = Math.min(remaining, row.quantity)
        remaining -= quantity
        row.quantity -= quantity
        return { batch_id: row.id, expiry_date: row.expiry_date, quantity }
      })
      .filter((row) => row.quantity > 0)
    return {
      product_id: body.product_id,
      store_id: 1,
      quantity: body.quantity,
      reason: body.reason,
      batches,
    }
  },

  async getSalesAnalytics(params: SalesAnalyticsParams = {}): Promise<SalesAnalytics> {
    return salesAnalytics(params)
  },

  async getInventoryAlerts(): Promise<InventoryAlerts> {
    return alerts
  },

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
      recommended_value: '99.9',
      current_price: prices.find((row) => row.product_id === productId)?.current_price ?? null,
      current_stock: 8,
      reasoning: 'Демо-рекомендация из mock-режима. Реальные данные появятся после подключения API.',
      confidence: 0.7,
      status: 'pending',
      expected_impact: '120.00',
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
}
