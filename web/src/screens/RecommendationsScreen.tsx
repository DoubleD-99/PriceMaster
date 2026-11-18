import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import {
  acceptRecommendation,
  generateRecommendations,
  listProducts,
  listRecommendations,
  rejectRecommendation,
} from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import type { SelectOption } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import { productName } from '../utils/catalog'
import { formatDateTime, formatMoney } from '../utils/format'
import {
  ACTION_LABELS,
  STATUS_LABELS,
  formatRecommendationValue,
} from '../utils/recommendations'
import type { Product, Recommendation, RecommendationStatus } from '../types/api'

const STATUS_OPTIONS: SelectOption[] = [
  { value: '', label: 'Все' },
  { value: 'pending', label: 'Ожидают' },
  { value: 'accepted', label: 'Принятые' },
  { value: 'rejected', label: 'Отклонённые' },
]

export function RecommendationsScreen() {
  const [products, setProducts] = useState<Product[]>([])
  const [status, setStatus] = useState<RecommendationStatus | ''>('pending')
  const [rows, setRows] = useState<Recommendation[]>([])
  const [limit, setLimit] = useState('10')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    listProducts()
      .then(setProducts)
      .catch((err: unknown) => setError(getErrorMessage(err)))
  }, [])

  useEffect(() => {
    let cancelled = false
    listRecommendations(status === '' ? undefined : status)
      .then((data) => {
        if (!cancelled) {
          setRows(data)
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
  }, [status, refreshKey])

  async function handleGenerate() {
    const parsed = Number(limit)
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 50) {
      setError('Лимит должен быть целым числом от 1 до 50.')
      return
    }
    setLoading(true)
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const created = await generateRecommendations({ limit: parsed })
      setStatus('pending')
      setNotice(
        created.length > 0
          ? `Создано рекомендаций: ${created.length}.`
          : 'Новых кандидатов для анализа нет.',
      )
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    } finally {
      setBusy(false)
    }
  }

  async function handleDecision(id: number, accept: boolean) {
    setLoading(true)
    setBusyId(id)
    setError(null)
    try {
      const updated = accept
        ? await acceptRecommendation(id)
        : await rejectRecommendation(id)
      setNotice(`Рекомендация №${updated.id}: ${STATUS_LABELS[updated.status].toLowerCase()}.`)
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Рекомендации</h1>
          <p className="muted">Предложения агента требуют подтверждения владельца</p>
        </div>
        <div className="row">
          <div className="field">
            <span className="field__label">Статус</span>
            <Select
              label="Статус"
              value={status}
              options={STATUS_OPTIONS}
              onChange={(next) => setStatus(next as RecommendationStatus | '')}
            />
          </div>
          <label className="field">
            <span className="field__label">Лимит анализа</span>
            <Input
              type="number"
              min={1}
              max={50}
              step={1}
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
            />
          </label>
          <div className="field field--action">
            <Button onClick={() => void handleGenerate()} disabled={busy}>
              {busy ? 'Анализ…' : 'Сгенерировать'}
            </Button>
          </div>
        </div>
      </div>
      {error && <Alert type="error">{error}</Alert>}
      {notice && <Alert type="success">{notice}</Alert>}
      <Card>
        {loading ? (
          <Spinner label="Загрузка рекомендаций…" />
        ) : rows.length === 0 ? (
          <p className="muted">Рекомендаций с таким статусом нет.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Товар</th>
                  <th>Действие</th>
                  <th>Значение</th>
                  <th>Обоснование</th>
                  <th>Эффект, ₽</th>
                  <th>Уверенность</th>
                  <th>Статус</th>
                  <th>Создана</th>
                  <th>Решение</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <Link to={`/products/${row.product_id}`}>
                        {productName(products, row.product_id)}
                      </Link>
                    </td>
                    <td>{ACTION_LABELS[row.action_type]}</td>
                    <td>{formatRecommendationValue(row)}</td>
                    <td className="table__reasoning">{row.reasoning}</td>
                    <td>{formatMoney(row.expected_impact)}</td>
                    <td>{Math.round(row.confidence * 100)}%</td>
                    <td>{STATUS_LABELS[row.status]}</td>
                    <td>{formatDateTime(row.created_at)}</td>
                    <td>
                      {row.status === 'pending' ? (
                        <div className="row">
                          <Button
                            variant="ghost"
                            disabled={busyId === row.id}
                            onClick={() => void handleDecision(row.id, true)}
                          >
                            Принять
                          </Button>
                          <Button
                            variant="ghost"
                            disabled={busyId === row.id}
                            onClick={() => void handleDecision(row.id, false)}
                          >
                            Отклонить
                          </Button>
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
