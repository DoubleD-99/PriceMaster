import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import { listStores } from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { useStoreContext } from '../stores/storeContext'
import type { Store } from '../types/api'

export function SettingsScreen() {
  const navigate = useNavigate()
  const storeId = useStoreContext((state) => state.storeId)
  const [stores, setStores] = useState<Store[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listStores()
      .then(setStores)
      .catch((err: unknown) => setError(getErrorMessage(err)))
  }, [])

  const current = stores.find((store) => store.id === storeId)

  return (
    <Card title="Настройки">
      <p>
        Текущий магазин: <strong>{current?.name ?? `№${storeId}`}</strong>
      </p>
      {current && (
        <p className="muted">
          {current.city}, {current.address}
        </p>
      )}
      {error && <Alert type="error">{error}</Alert>}
      <div className="row">
        <Button onClick={() => navigate('/select-store')}>Сменить магазин</Button>
      </div>
    </Card>
  )
}
