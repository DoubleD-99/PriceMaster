import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'

import { api } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { useAuthStore } from '../stores/authStore'

// Контракт POST /auth/login (SDD §A.5): { token, user_info }.
interface LoginResponse {
  token: string
}

export function AuthScreen() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [accessKey, setAccessKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post<LoginResponse>('/auth/login', {
        access_key: accessKey,
      })
      login(data.token)
      navigate('/select-store')
    } catch (err) {
      if (isAxiosError(err) && err.response) {
        setError(
          err.response.status === 401 || err.response.status === 403
            ? 'Неверный ключ доступа.'
            : 'Ошибка сервера. Попробуйте позже.',
        )
      } else {
        setError('Сервер недоступен. Проверьте соединение.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="screen screen--center">
      <Card title="PriceMaster">
        <p className="muted">Введите ключ доступа магазина</p>
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
