import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { useAuthStore } from '../stores/authStore'

interface LoginResponse {
  access_token: string
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
      login(data.access_token)
      navigate('/select-store')
    } catch {
      setError('Не удалось войти. Проверьте ключ доступа.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="screen screen--center">
      <form className="card" onSubmit={handleSubmit}>
        <h1>PriceMaster</h1>
        <p className="muted">Введите ключ доступа магазина</p>
        <input
          type="password"
          value={accessKey}
          onChange={(event) => setAccessKey(event.target.value)}
          placeholder="Access Key"
          autoComplete="current-password"
          required
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Вход…' : 'Войти'}
        </button>
      </form>
    </main>
  )
}
