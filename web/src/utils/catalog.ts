import type { Product } from '../types/api'

export function productName(products: Product[], productId: number): string {
  return products.find((product) => product.id === productId)?.name ?? `Товар #${productId}`
}
