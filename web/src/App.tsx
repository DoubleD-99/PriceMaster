import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { AuthScreen } from './screens/AuthScreen'
import { DashboardHome } from './screens/DashboardHome'
import { StoreSelector } from './screens/StoreSelector'
import { InventoryScreen } from './screens/InventoryScreen'
import { RecommendationsScreen } from './screens/RecommendationsScreen'
import { ScannerScreen } from './screens/ScannerScreen'
import { SettingsScreen } from './screens/SettingsScreen'
import { useAuthStore } from './stores/authStore'

function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuthStore((state) => state.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<AuthScreen />} />
        <Route
          path="/select-store"
          element={
            <RequireAuth>
              <StoreSelector />
            </RequireAuth>
          }
        />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardHome />} />
          <Route path="inventory" element={<InventoryScreen />} />
          <Route path="recommendations" element={<RecommendationsScreen />} />
          <Route path="scanner" element={<ScannerScreen />} />
          <Route path="settings" element={<SettingsScreen />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
