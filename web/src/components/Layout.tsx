import { Outlet, NavLink, useNavigate } from 'react-router-dom'

import { StoreSelect } from './StoreSelect'
import { useNetworkStatus } from '../hooks/useNetworkStatus'
import { useAuthStore } from '../stores/authStore'
import { useStoreContext } from '../stores/storeContext'

export function Layout() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)
  const storeId = useStoreContext((state) => state.storeId)
  const { online } = useNetworkStatus()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app">
      {!online && (
        <div className="offline-banner" role="status">
          Нет связи с сервером. Данные могут быть устаревшими; приёмка, списание и решение по
          рекомендациям недоступны.
        </div>
      )}
      <header className="topbar">
        <nav className="nav">
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Дашборд
          </NavLink>
          <NavLink to="/recommendations" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Рекомендации
          </NavLink>
          <NavLink to="/inventory" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Склад
          </NavLink>
          <NavLink to="/analytics" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Аналитика
          </NavLink>
          <NavLink to="/scanner" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Сканер ШК
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Настройки
          </NavLink>
        </nav>
        <div className="topbar__right">
          <StoreSelect />
          <button type="button" className="btn btn--ghost btn--logout" onClick={handleLogout}>
            Выйти
          </button>
        </div>
      </header>
      <main className="screen">
        <Outlet key={storeId ?? 'none'} />
      </main>
    </div>
  )
}
