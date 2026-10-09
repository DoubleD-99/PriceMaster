import { useNavigate } from 'react-router-dom'

import { useAuthStore } from '../stores/authStore'
import { useStoreContext } from '../stores/storeContext'

export function DashboardHome() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const storeId = useStoreContext((state) => state.storeId)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <main className="screen">
      <header className="topbar">
        <strong>PriceMaster</strong>
        <span className="muted">Магазин #{storeId ?? '—'}</span>
        <button type="button" onClick={handleLogout}>
          Выйти
        </button>
      </header>
      <section className="card">
        <h1>Дашборд</h1>
        <p className="muted">
          Экраны KPI, рекомендаций и аналитики появятся в следующих итерациях
          (SDD, A.10).
        </p>
      </section>
    </main>
  )
}
