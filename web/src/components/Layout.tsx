import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useStoreContext } from '../stores/storeContext'

export function Layout() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const storeId = useStoreContext((state) => state.storeId)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app">
      <header className="topbar">
        <nav className="nav">
          <NavLink to="/" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Дашборд
          </NavLink>
          <NavLink to="/inventory" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Склад
          </NavLink>
          <NavLink to="/recommendations" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Рекомендации
          </NavLink>
          <NavLink to="/scanner" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Сканер ШК
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Настройки
          </NavLink>
        </nav>
        <div className="topbar__right">
          <span className="muted">Магазин: #{storeId ?? '—'}</span>
          <button type="button" className="btn btn--ghost" onClick={handleLogout}>
            Выйти
          </button>
        </div>
      </header>
      <main className="screen">
        <Outlet />
      </main>
    </div>
  )
}
