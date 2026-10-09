import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { useStoreContext } from '../stores/storeContext'

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
      <section className="card">
        <h1>Выбор магазина</h1>
        {loading && <p className="muted">Загрузка…</p>}
        {error && <p className="error">{error}</p>}
        <ul className="list">
          {stores.map((store) => (
            <li key={store.id}>
              <button type="button" onClick={() => handleSelect(store.id)}>
                {store.name}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
