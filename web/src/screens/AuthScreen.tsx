import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { getLoginErrorMessage } from '../api/errors'
import { login as loginRequest } from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { useAuthStore } from '../stores/authStore'
import { useStoreContext } from '../stores/storeContext'

export function AuthScreen() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const setStoreId = useStoreContext((state) => state.setStoreId)
  const [accessKey, setAccessKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await loginRequest(accessKey)
      login(result.token)
      setStoreId(null)
      navigate('/select-store')
    } catch (err) {
      setError(getLoginErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="screen screen--center">
      <Card title="PriceMaster">
        <p className="muted">Введите ключ доступа</p>
        <form className="stack" onSubmit={handleSubmit}>
          <Input
            type="password"
            value={accessKey}
            onChange={(event) => setAccessKey(event.target.value)}
            placeholder="Access Key"
            autoComplete="current-password"
          />
          {error && <Alert type="error">{error}</Alert>}
          <Button type="submit" disabled={loading}>
            {loading ? 'Вход…' : 'Войти'}
          </Button>
        </form>
      </Card>
    </main>
  )
}
