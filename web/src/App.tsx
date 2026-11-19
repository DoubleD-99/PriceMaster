import { lazy, Suspense } from 'react'
import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Spinner } from './components/ui/Spinner'
import { AuthScreen } from './screens/AuthScreen'
import { DashboardHome } from './screens/DashboardHome'
import { StoreSelector } from './screens/StoreSelector'
import { InventoryScreen } from './screens/InventoryScreen'
import { RecommendationsScreen } from './screens/RecommendationsScreen'
import { ScannerScreen } from './screens/ScannerScreen'
import { SettingsScreen } from './screens/SettingsScreen'
import { useAuthStore } from './stores/authStore'
import { useStoreContext } from './stores/storeContext'

function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuthStore((state) => state.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

function RequireStore({ children }: { children: ReactNode }) {
  const storeId = useStoreContext((state) => state.storeId)
  return storeId === null ? <Navigate to="/select-store" replace /> : <>{children}</>
}

const AnalyticsScreen = lazy(() =>
  import('./screens/AnalyticsScreen').then((module) => ({ default: module.AnalyticsScreen })),
)
const ProductCardScreen = lazy(() =>
  import('./screens/ProductCardScreen').then((module) => ({ default: module.ProductCardScreen })),
)

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Spinner label="Загрузка экрана…" />}>
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
                <RequireStore>
                  <Layout />
                </RequireStore>
              </RequireAuth>
            }
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardHome />} />
            <Route path="inventory" element={<InventoryScreen />} />
            <Route path="products/:productId" element={<ProductCardScreen />} />
            <Route path="analytics" element={<AnalyticsScreen />} />
            <Route path="recommendations" element={<RecommendationsScreen />} />
            <Route path="scanner" element={<ScannerScreen />} />
            <Route path="settings" element={<SettingsScreen />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
