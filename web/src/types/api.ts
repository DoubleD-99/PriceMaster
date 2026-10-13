export type Store = {
  id: number
  name: string
  code: string
  city: string | null
  address: string | null
  phone: string | null
  is_active: boolean
  created_at: string
}

export type Product = {
  id: number
  sku: string
  name: string
  barcode: string | null
  brand: string | null
  category_id: number | null
  unit: string
  purchase_price: number
  markup_percent: number | null
  min_price: number | null
  max_price: number | null
  vat_rate: number | null
  is_active: boolean
  created_at: string
}

export type InventoryItem = {
  id: number
  store_id: number
  product_id: number
  qty_on_hand: number
  qty_reserved: number
  last_movement_at: string | null
}

export type Barcode = {
  id: number
  product_id: number
  barcode: string
  created_at: string
}

export type Recommendation = {
  id: number
  store_id: number
  product_id: number
  current_price: number
  recommended_price: number
  reason_code: string
  reason_text: string | null
  confidence: number | null
  status: 'NEW' | 'ACCEPTED' | 'REJECTED' | 'EXPIRED' | 'APPLIED'
  applied_at: string | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

export type ApiError = {
  detail: string | { [key: string]: string[] }
}
