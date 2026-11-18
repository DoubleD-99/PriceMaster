import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from './client'
import { useAuthStore } from '../stores/authStore'
import { useNetworkStore } from '../stores/networkStore'
import { useStoreContext } from '../stores/storeContext'

function createAdapter() {
  return vi.fn(async (config) => ({
    data: {},
    status: 200,
    statusText: 'OK',
    headers: {},
    config,
  }))
}

describe('api request interceptor', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    useAuthStore.setState({ token: null })
    useStoreContext.setState({ storeId: null })
    useNetworkStore.setState({ backendOnline: true })
  })

  it('adds Authorization and X-Store-ID headers', async () => {
    const adapter = createAdapter()
    useAuthStore.setState({ token: 'jwt-token' })
    useStoreContext.setState({ storeId: 3 })

    await api.get('/stores', { adapter })

    const config = adapter.mock.calls[0][0]
    expect(config.headers.Authorization).toBe('Bearer jwt-token')
    expect(config.headers['X-Store-ID']).toBe('3')
  })

  it('does not add X-Store-ID when no store is selected', async () => {
    const adapter = createAdapter()

    await api.get('/stores', { adapter })

    const config = adapter.mock.calls[0][0]
    expect(config.headers['X-Store-ID']).toBeUndefined()
  })

  it('blocks mutations when the backend is offline', async () => {
    const adapter = createAdapter()
    useNetworkStore.setState({ backendOnline: false })

    await expect(api.post('/wms/receiving', {}, { adapter })).rejects.toThrow(
      'Нет связи с сервером',
    )
    expect(adapter).not.toHaveBeenCalled()
  })
})
