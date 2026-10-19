import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { useStoreContext } from '../stores/storeContext'

// GET /stores (SDD §A.5): список магазинов, доступных токену.
interface Store {
  id: number
  name: string
}

export function StoreSelector() {
  const navigate = useNavigate()
  const setStoreId = useStoreContext((state) => state.setStoreId)
  const [stores, setStores] = useState<Store[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<Store[]>('/stores')
      .then((response) => setStores(response.data))
      .catch(() => setError('Не удалось загрузить список магазинов.'))
      .finally(() => setLoading(false))
  }, [])

  function handleSelect(id: number) {
    setStoreId(id)
    navigate('/')
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
