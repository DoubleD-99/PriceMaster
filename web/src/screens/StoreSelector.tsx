import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import { listStores } from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { useStoreContext } from '../stores/storeContext'
import type { Store } from '../types/api'

export function StoreSelector() {
  const navigate = useNavigate()
  const setStoreId = useStoreContext((state) => state.setStoreId)
  const [stores, setStores] = useState<Store[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    listStores()
      .then((rows) => {
        if (!cancelled) setStores(rows)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function handleSelect(id: number) {
    setStoreId(id)
    navigate('/dashboard')
  }

  return (
    <main className="screen screen--center">
      <Card title="Выбор магазина">
        {loading && <Spinner label="Загрузка магазинов…" />}
        {error && <Alert type="error">{error}</Alert>}
        <ul className="list">
          {stores.map((store) => (
            <li key={store.id}>
              <Button variant="ghost" onClick={() => handleSelect(store.id)}>
                {store.name}
              </Button>
            </li>
          ))}
        </ul>
      </Card>
    </main>
  )
}
