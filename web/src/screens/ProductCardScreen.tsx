import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import {
  generateRecommendations,
  getPriceHistory,
  getProductPrice,
  getSalesAnalytics,
  listInventory,
  listProducts,
  listRecommendations,
} from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { formatDate, formatDateTime, formatMoney, formatQuantity, toNumber } from '../utils/format'
import { ACTION_LABELS } from '../utils/recommendations'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type {
  InventoryItem,
  PriceHistoryEntry,
  Product,
  ProductPrice,
  Recommendation,
  SalesAnalytics,
} from '../types/api'

const TOOLTIP_CONTENT_STYLE = {
  background: '#ffffff',
  border: '1px solid #232a45',
  borderRadius: 10,
  color: '#0b1026',
  boxShadow: '0 12px 30px -12px rgba(0, 0, 0, 0.6)',
}
const TOOLTIP_TEXT_STYLE = { color: '#0b1026' }
const TOOLTIP_VALUE_STYLE = { color: '#2563eb', fontWeight: 600 }

function formatTooltipValue(value: unknown, name: unknown) {
  return [
    <span key="value" style={TOOLTIP_VALUE_STYLE}>
      {String(value)}
    </span>,
    String(name),
  ]
}

export function ProductCardScreen() {
  const { productId } = useParams<{ productId: string }>()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [sales, setSales] = useState<SalesAnalytics | null>(null)
  const [price, setPrice] = useState<ProductPrice | null>(null)
  const [priceHistory, setPriceHistory] = useState<PriceHistoryEntry[]>([])
  const [accepted, setAccepted] = useState<Recommendation[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [recommendationsLoading, setRecommendationsLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const id = Number(productId)

  useEffect(() => {
    let cancelled = false

    Promise.all([
      listProducts(),
      listInventory(id),
      getSalesAnalytics({ product_id: id }),
      getProductPrice(id),
      getPriceHistory(id),
      listRecommendations('accepted'),
    ])
      .then(([products, batches, salesRows, priceRow, historyRows, recommendations]) => {
        if (cancelled) return
        setProduct(products.find((row) => row.id === id) ?? null)
        setInventory(batches)
        setSales(salesRows)
        setPrice(priceRow)
        setPriceHistory(historyRows)
        setAccepted(
          recommendations.filter(
            (row) => row.product_id === id && row.action_type === 'price_change',
          ),
        )
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
  }, [id, refreshKey])

  async function handleAnalyze() {
    setRecommendationsLoading(true)
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const created = await generateRecommendations({ product_id: id })
      setNotice(
        created.length > 0
          ? `Создана рекомендация №${created[0].id}.`
          : 'Агент не создал рекомендацию для этого товара.',
      )
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRecommendationsLoading(false)
      setBusy(false)
    }
  }

  if (!Number.isInteger(id) || id < 1) {
    return <Alert type="error">Некорректный идентификатор товара.</Alert>
  }
  if (loading) return <Spinner label="Загрузка карточки товара…" />

  const totalQuantity = inventory.reduce((sum, row) => sum + row.quantity, 0)
  const chartData = (sales?.by_day ?? []).map((row) => ({
    date: row.date.slice(5),
    revenue: toNumber(row.revenue),
    quantity: row.quantity,
  }))
  const priceChartData = [...priceHistory].reverse().map((row) => ({
    date: row.changed_at.slice(5, 10),
    price: toNumber(row.new_price),
  }))

  return (
    <>
      <div className="page-header">
        <div>
          <Link to="/inventory" className="muted">
            ← Склад
          </Link>
          <h1>{product?.name ?? `Товар #${id}`}</h1>
          <p className="muted">{product?.category ?? 'Категория не загружена'}</p>
        </div>
        <div className="row">
          <Button
            variant="ghost"
            onClick={() => navigate(`/inventory?product_id=${id}&operation=receiving`)}
          >
            Приёмка
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate(`/inventory?product_id=${id}&operation=write_off`)}
          >
            Списание
          </Button>
          <Button onClick={() => void handleAnalyze()} disabled={busy}>
            {busy ? 'Анализ…' : 'Анализ товара'}
          </Button>
        </div>
      </div>
      {error && <Alert type="error">{error}</Alert>}
      {notice && <Alert type="success">{notice}</Alert>}
      {recommendationsLoading && <Spinner label="Генерация рекомендации…" />}
      {product === null && !error && <Alert type="warning">Товар не найден в каталоге.</Alert>}
      <div className="kpi-grid">
        <Card title="Себестоимость">
          <strong className="kpi-value">{formatMoney(product?.base_cost ?? '0')} ₽</strong>
        </Card>
        <Card title="Текущая цена">
          <strong className="kpi-value">
            {price ? `${formatMoney(price.current_price, 1)} ₽` : '—'}
          </strong>
        </Card>
        <Card title="Остаток">
          <strong className="kpi-value">{formatQuantity(totalQuantity)} шт.</strong>
        </Card>
        <Card title="Минимальный остаток">
          <strong className="kpi-value">{formatQuantity(product?.min_stock ?? 0)} шт.</strong>
        </Card>
        <Card title="Срок годности">
          <strong className="kpi-value">{product?.shelf_life_days ?? 0} дн.</strong>
        </Card>
      </div>
      <Card title="График продаж">
        {chartData.length === 0 ? (
          <p className="muted">Продаж за выбранный период нет.</p>
        ) : (
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232a45" />
                <XAxis dataKey="date" tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                <Tooltip
                  contentStyle={TOOLTIP_CONTENT_STYLE}
                  labelStyle={TOOLTIP_TEXT_STYLE}
                  itemStyle={TOOLTIP_TEXT_STYLE}
                  formatter={formatTooltipValue}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  name="Выручка, ₽"
                  stroke="#60a5fa"
                  fill="rgba(37, 99, 235, 0.3)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      <Card title="График цены">
        {priceChartData.length === 0 ? (
          <p className="muted">Изменений цены за период нет.</p>
        ) : (
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={priceChartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232a45" />
                <XAxis dataKey="date" tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                <Tooltip
                  contentStyle={TOOLTIP_CONTENT_STYLE}
                  labelStyle={TOOLTIP_TEXT_STYLE}
                  itemStyle={TOOLTIP_TEXT_STYLE}
                  formatter={formatTooltipValue}
                />
                <Area
                  type="monotone"
                  dataKey="price"
                  name="Цена, ₽"
                  stroke="#2563eb"
                  fill="rgba(37, 99, 235, 0.3)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      {accepted.length > 0 && (
        <Card title="Обоснования принятых решений">
          <ul className="list">
            {accepted.map((row) => (
              <li key={row.id} className="list-row">
                <span>{ACTION_LABELS[row.action_type]}</span>
                <span className="muted">{row.reasoning}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <div className="info-grid">
        <Card title="Остатки по партиям">
          {inventory.length === 0 ? (
            <p className="muted">Партий нет.</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Партия</th>
                    <th>Дата партии</th>
                    <th>Годен до</th>
                    <th>Остаток</th>
                  </tr>
                </thead>
                <tbody>
                  {inventory.map((batch) => (
                    <tr key={batch.id}>
                      <td>№{batch.id}</td>
                      <td>{formatDate(batch.batch_date)}</td>
                      <td>{formatDate(batch.expiry_date)}</td>
                      <td>{formatQuantity(batch.quantity)} шт.</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="История цен">
          {priceHistory.length === 0 ? (
            <p className="muted">Изменений цены нет.</p>
          ) : (
            <ul className="list">
              {priceHistory.map((row) => (
                <li key={row.id} className="list-row">
                  <span>
                    {formatMoney(row.old_price)} ₽ → <strong>{formatMoney(row.new_price)} ₽</strong>
                  </span>
                  <span className="muted">{formatDateTime(row.changed_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
