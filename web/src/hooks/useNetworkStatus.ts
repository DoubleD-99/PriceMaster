import { useEffect } from 'react'

import { checkHealth } from '../api/endpoints'
import { useNetworkStore } from '../stores/networkStore'

export function useNetworkStatus() {
  const backendOnline = useNetworkStore((state) => state.backendOnline)
  const setBackendOnline = useNetworkStore((state) => state.setBackendOnline)

  useEffect(() => {
    let cancelled = false

    async function check() {
      const online = navigator.onLine ? await checkHealth() : false
      if (!cancelled) setBackendOnline(online)
    }

    const handleChange = () => void check()
    window.addEventListener('online', handleChange)
    window.addEventListener('offline', handleChange)
    window.addEventListener('focus', handleChange)
    void check()
    const timer = window.setInterval(handleChange, 60_000)

    return () => {
      cancelled = true
      window.removeEventListener('online', handleChange)
      window.removeEventListener('offline', handleChange)
      window.removeEventListener('focus', handleChange)
      window.clearInterval(timer)
    }
  }, [setBackendOnline])

  return {
    online: navigator.onLine && backendOnline !== false,
    backendOnline,
  }
}
