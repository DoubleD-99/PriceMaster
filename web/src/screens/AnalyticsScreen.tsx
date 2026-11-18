import { useEffect, useState } from 'react'

import { getErrorMessage } from '../api/errors'
import { getSalesAnalytics, listProducts } from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import { productName } from '../utils/catalog'
import { addDaysISO, formatDate, formatMoney, formatQuantity, todayISO, toNumber } from '../utils/format'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Product, SalesAnalytics } from '../types/api'

const TOOLTIP_CONTENT_STYLE = {
  background: '#ffffff',
  border: '1px solid #232a45',
  borderRadius: 10,
  color: '#0b1026',
  boxShadow: '0 12px 30px -12px rgba(0, 0, 0, 0.6)',
}
const TOOLTIP_TEXT_STYLE = { color: '#0b1026' }

export function AnalyticsScreen() {
  const [products, setProducts] = useState<Product[]>([])
  const [dateFrom, setDateFrom] = useState(addDaysISO(-29))
  const [dateTo, setDateTo] = useState(todayISO())
  const [productId, setProductId] = useState('')
  const [data, setData] = useState<SalesAnalytics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    listProducts()
      .then(setProducts)
      .catch((err: unknown) => setError(getErrorMessage(err)))
  }, [])

  useEffect(() => {
    let cancelled = false
    getSalesAnalytics({
      date_from: dateFrom,
      date_to: dateTo,
      product_id: productId === '' ? undefined : Number(productId),
    })
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setError(null)
        }
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
  }, [dateFrom, dateTo, productId, refreshKey])

  const byDay = (data?.by_day ?? []).map((row) => ({
    date: row.date.slice(5),
    revenue: toNumber(row.revenue),
    quantity: row.quantity,
  }))
  const byProduct = (data?.by_product ?? []).map((row) => ({
    name: productName(products, row.product_id),
    revenue: toNumber(row.revenue),
    quantity: row.quantity,
  }))

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Аналитика продаж</h1>
          <p className="muted">Выручка и количество продаж в выбранном периоде</p>
        </div>
      </div>
      <Card>
        <div className="filters">
          <label className="field">
            <span className="field__label">Дата от</span>
            <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label className="field">
            <span className="field__label">Дата до</span>
            <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <div className="field">
            <span className="field__label">Товар</span>
            <Select
              label="Товар"
              value={productId}
              fullWidth
              placeholder="Все товары"
              options={[
                { value: '', label: 'Все товары' },
                ...products.map((product) => ({
                  value: String(product.id),
                  label: product.name,
                  helper: `#${product.id}`,
                })),
              ]}
              onChange={setProductId}
            />
          </div>
          <div className="field field--action">
            <Button
              onClick={() => {
                if (dateFrom > dateTo) {
                  setError('Дата «от» не может быть позже даты «до».')
                  return
                }
                setError(null)
                setLoading(true)
                setRefreshKey((key) => key + 1)
              }}
            >
              Применить
            </Button>
          </div>
        </div>
      </Card>
      {error && <Alert type="error">{error}</Alert>}
      {loading ? (
        <Spinner label="Загрузка аналитики…" />
      ) : (
        <>
          <div className="kpi-grid">
            <Card title="Выручка">
              <strong className="kpi-value">{formatMoney(data?.summary.total_revenue ?? '0')} ₽</strong>
            </Card>
            <Card title="Продано">
              <strong className="kpi-value">{formatQuantity(data?.summary.total_quantity ?? 0)} шт.</strong>
            </Card>
            <Card title="Продаж">
              <strong className="kpi-value">{formatQuantity(data?.summary.sales_count ?? 0)}</strong>
            </Card>
            <Card title="Средний чек">
              <strong className="kpi-value">{formatMoney(data?.summary.average_check ?? '0')} ₽</strong>
            </Card>
          </div>
          <div className="two-column">
            <Card title="Выручка по дням">
              {byDay.length === 0 ? (
                <p className="muted">Нет продаж в выбранном периоде.</p>
              ) : (
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={byDay} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#232a45" />
                      <XAxis dataKey="date" tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                      <YAxis tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                      <Tooltip
                    contentStyle={TOOLTIP_CONTENT_STYLE}
                    labelStyle={TOOLTIP_TEXT_STYLE}
                    itemStyle={TOOLTIP_TEXT_STYLE}
                  />
                      <Bar dataKey="revenue" name="Выручка, ₽" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
            <Card title="Выручка по товарам">
              {byProduct.length === 0 ? (
                <p className="muted">Нет продаж в выбранном периоде.</p>
              ) : (
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={byProduct}
                      layout="vertical"
                      margin={{ top: 8, right: 12, left: 8, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#232a45" />
                      <XAxis type="number" tick={{ fill: '#9aa0c3', fontSize: 12 }} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={130}
                        tick={{ fill: '#9aa0c3', fontSize: 12 }}
                      />
                      <Tooltip
                    contentStyle={TOOLTIP_CONTENT_STYLE}
                    labelStyle={TOOLTIP_TEXT_STYLE}
                    itemStyle={TOOLTIP_TEXT_STYLE}
                  />
                      <Bar dataKey="revenue" name="Выручка, ₽" fill="#22c55e" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>
          <Card title="Детализация по дням">
            {(data?.by_day ?? []).length === 0 ? (
              <p className="muted">Нет данных.</p>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Выручка</th>
                      <th>Количество</th>
                      <th>Продаж</th>
                      <th>Средний чек</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data?.by_day ?? []).map((row) => (
                      <tr key={row.date}>
                        <td>{formatDate(row.date)}</td>
                        <td>{formatMoney(row.revenue)} ₽</td>
                        <td>{formatQuantity(row.quantity)} шт.</td>
                        <td>{formatQuantity(row.sales_count)}</td>
                        <td>{formatMoney(row.average_check)} ₽</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </>
  )
}
