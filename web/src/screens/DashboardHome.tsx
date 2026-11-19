import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import {
  acceptRecommendation,
  getInventoryAlerts,
  getSalesAnalytics,
  listProducts,
  listRecommendations,
  rejectRecommendation,
} from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { productName } from '../utils/catalog'
import { formatDate, formatMoney, formatQuantity, todayISO } from '../utils/format'
import { ACTION_LABELS, formatRecommendationValue } from '../utils/recommendations'
import type {
  ExpiringBatchAlert,
  InventoryAlerts,
  Product,
  Recommendation,
  SalesAnalytics,
} from '../types/api'

export function DashboardHome() {
  const [products, setProducts] = useState<Product[]>([])
  const [alerts, setAlerts] = useState<InventoryAlerts>({ expiring_soon: [], low_stock: [] })
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [sales, setSales] = useState<SalesAnalytics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      listProducts(),
      getInventoryAlerts(),
      listRecommendations('pending'),
      getSalesAnalytics({ date_from: todayISO(), date_to: todayISO() }),
    ])
      .then(([productRows, alertRows, recommendationRows, salesRows]) => {
        if (cancelled) return
        setProducts(productRows)
        setAlerts(alertRows)
        setRecommendations(recommendationRows)
        setSales(salesRows)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  async function handleDecision(id: number, accept: boolean) {
    setLoading(true)
    setBusyId(id)
    setError(null)
    try {
      const updated = accept
        ? await acceptRecommendation(id)
        : await rejectRecommendation(id)
      setNotice(`Рекомендация №${updated.id}: ${updated.status === 'accepted' ? 'принята' : 'отклонена'}.`)
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    } finally {
      setBusyId(null)
    }
  }

  const expiringByProduct = new Map<number, ExpiringBatchAlert>()
  for (const alert of alerts.expiring_soon) {
    const current = expiringByProduct.get(alert.product_id)
    if (!current || alert.expiry_date < current.expiry_date) {
      expiringByProduct.set(alert.product_id, alert)
    }
  }
  const expiringProducts = [...expiringByProduct.values()]

  if (loading) return <Spinner label="Загрузка дашборда…" />

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Дашборд</h1>
          <p className="muted">Ключевые показатели и сигналы выбранного магазина</p>
        </div>
        <div className="row">
          <Button
            onClick={() => {
              setLoading(true)
              setRefreshKey((key) => key + 1)
            }}
            variant="ghost"
          >
            Обновить
          </Button>
        </div>
      </div>
      {error && <Alert type="error">{error}</Alert>}
      {notice && <Alert type="success">{notice}</Alert>}
      <div className="kpi-grid">
        <Card title="Выручка за сегодня">
          <strong className="kpi-value">{formatMoney(sales?.summary.total_revenue ?? '0')} ₽</strong>
        </Card>
        <Card title="Продано за сегодня">
          <strong className="kpi-value">{formatQuantity(sales?.summary.total_quantity ?? 0)} шт.</strong>
        </Card>
        <Card title="Требуют решения">
          <strong className="kpi-value">{recommendations.length}</strong>
        </Card>
        <Card title="Предупреждения">
          <strong className="kpi-value">
            {expiringProducts.length + alerts.low_stock.length}
          </strong>
        </Card>
      </div>
      <div className="two-column">
        <Card title={<Link to="/recommendations">Топ рекомендаций</Link>}>
          {recommendations.length === 0 ? (
            <p className="muted">
              Ожидающих рекомендаций нет. Запустите анализ в разделе «Рекомендации».
            </p>
          ) : (
            <ul className="list">
              {recommendations.slice(0, 3).map((recommendation) => (
                <li key={recommendation.id} className="list-row">
                  <div className="list-row__main">
                    <Link to={`/products/${recommendation.product_id}`}>
                      {productName(products, recommendation.product_id)}
                    </Link>
                    <div className="muted">
                      {ACTION_LABELS[recommendation.action_type]} ·{' '}
                      {formatRecommendationValue(recommendation)}
                    </div>
                  </div>
                  <div className="row decision-actions">
                    <Button
                      variant="success"
                      disabled={busyId === recommendation.id}
                      onClick={() => void handleDecision(recommendation.id, true)}
                    >
                      Принять
                    </Button>
                    <Button
                      variant="danger"
                      disabled={busyId === recommendation.id}
                      onClick={() => void handleDecision(recommendation.id, false)}
                    >
                      Отклонить
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Предупреждения">
          <h3>Истекающий срок годности</h3>
          {expiringProducts.length === 0 ? (
            <p className="muted">Нет партий с истекающим сроком.</p>
          ) : (
            <ul className="list">
              {expiringProducts.map((alert) => (
                <li key={alert.product_id} className="list-row">
                  <Link to={`/products/${alert.product_id}`}>
                    {productName(products, alert.product_id)}
                  </Link>
                  <span className="muted">
                    до {formatDate(alert.expiry_date)} · {alert.days_left} дн.
                  </span>
                </li>
              ))}
            </ul>
          )}
          <h3>Ниже минимального остатка</h3>
          {alerts.low_stock.length === 0 ? (
            <p className="muted">Все остатки выше минимума.</p>
          ) : (
            <ul className="list">
              {alerts.low_stock.map((alert) => (
                <li key={alert.product_id} className="list-row">
                  <Link to={`/products/${alert.product_id}`}>
                    {productName(products, alert.product_id)}
                  </Link>
                  <span className="muted">
                    {formatQuantity(alert.quantity)} / {formatQuantity(alert.min_stock)} шт.
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link to="/inventory">Открыть складские операции</Link>
        </Card>
      </div>
    </>
  )
}
