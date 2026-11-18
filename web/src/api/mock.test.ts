import { describe, expect, it } from 'vitest'

import { mockApi } from './mock'
import { addDaysISO, todayISO } from '../utils/format'

describe('demo data flow', () => {
  it('supports scan, receiving, alerts, recommendation, accept and analytics', async () => {
    const product = await mockApi.lookupBarcode('4600000000001')
    const receiving = await mockApi.createReceiving({
      product_id: product.id,
      quantity: 5,
      batch_date: todayISO(),
      expiry_date: addDaysISO(2),
    })
    const alerts = await mockApi.getInventoryAlerts()
    const created = await mockApi.generateRecommendations({ product_id: product.id })
    const accepted = await mockApi.acceptRecommendation(created[0].id)
    const analytics = await mockApi.getSalesAnalytics({ product_id: product.id })

    expect(receiving.quantity_added).toBe(5)
    expect(alerts.expiring_soon.some((alert) => alert.product_id === product.id)).toBe(true)
    expect(accepted.status).toBe('accepted')
    expect(analytics.by_product.length).toBe(1)
    expect(analytics.by_day.length).toBeGreaterThan(0)
  })
})
