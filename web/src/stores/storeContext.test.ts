import { beforeEach, describe, expect, it } from 'vitest'

import { useStoreContext } from './storeContext'

describe('useStoreContext', () => {
  beforeEach(() => {
    localStorage.clear()
    useStoreContext.setState({ storeId: null })
  })

  it('persists the selected store in localStorage', () => {
    useStoreContext.getState().setStoreId(7)

    expect(useStoreContext.getState().storeId).toBe(7)
    expect(localStorage.getItem('pricemaster-store')).toContain('"storeId":7')
  })

  it('allows clearing the selected store', () => {
    useStoreContext.getState().setStoreId(7)
    useStoreContext.getState().setStoreId(null)

    expect(useStoreContext.getState().storeId).toBeNull()
  })
})
