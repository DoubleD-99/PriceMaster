import { Outlet, NavLink, useNavigate } from 'react-router-dom'

import { StoreSelect } from './StoreSelect'
import { useAuthStore } from '../stores/authStore'

export function Layout() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)

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
          <NavLink to="/recommendations" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Рекомендации
          </NavLink>
          <NavLink to="/inventory" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Склад
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
        <Outlet />
      </main>
    </div>
  )
}
