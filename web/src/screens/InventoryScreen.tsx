import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import {
  createReceiving,
  createWriteOff,
  listInventory,
  listProducts,
  lookupBarcode,
} from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import { addDaysISO, formatDate, formatQuantity, todayISO } from '../utils/format'
import type { InventoryItem, Product } from '../types/api'

type Operation = 'receiving' | 'write_off'

const WRITE_OFF_REASONS = ['Порча', 'Истечение срока', 'Ошибка приёмки', 'Другое']

export function InventoryScreen() {
  const [searchParams] = useSearchParams()
  const barcodeParam = searchParams.get('barcode')
  const productParam = searchParams.get('product_id')
  const [operation, setOperation] = useState<Operation>(
    searchParams.get('operation') === 'write_off' ? 'write_off' : 'receiving',
  )
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState(productParam ?? '')
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [quantity, setQuantity] = useState('1')
  const [batchDate, setBatchDate] = useState(todayISO())
  const [expiryDate, setExpiryDate] = useState(addDaysISO(7))
  const [expiryTouched, setExpiryTouched] = useState(false)
  const [reason, setReason] = useState(WRITE_OFF_REASONS[0])
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    listProducts()
      .then((rows) => setProducts(rows))
      .catch((err: unknown) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (barcodeParam === null) return
    lookupBarcode(barcodeParam)
      .then((product) => setProductId(String(product.id)))
      .catch((err: unknown) => setError(`Штрих-код не найден: ${getErrorMessage(err)}`))
  }, [barcodeParam])

  useEffect(() => {
    if (productId === '') return
    let cancelled = false
    listInventory(Number(productId))
      .then((rows) => {
        if (!cancelled) setInventory(rows)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [productId, refreshKey])

  const selectedProduct = products.find((row) => String(row.id) === productId)
  const productOptions = [
    { value: '', label: 'Выберите товар' },
    ...products.map((product) => ({
      value: String(product.id),
      label: product.name,
      helper: `#${product.id}`,
    })),
  ]
  const reasonOptions = [
    ...WRITE_OFF_REASONS.map((item) => ({ value: item, label: item })),
    ...(WRITE_OFF_REASONS.includes(reason) ? [] : [{ value: reason, label: reason }]),
  ]
  const effectiveExpiryDate = expiryTouched
    ? expiryDate
    : addDaysISO(selectedProduct?.shelf_life_days ?? 7)
  const visibleInventory = productId === '' ? [] : inventory
  const totalQuantity = visibleInventory.reduce((sum, row) => sum + row.quantity, 0)

  function validate(): number | null {
    setError(null)
    setSuccess(null)
    const parsed = Number(quantity)
    if (!Number.isInteger(parsed) || parsed < 1) {
      setError('Количество должно быть целым числом больше нуля.')
      return null
    }
    if (productId === '') {
      setError('Выберите товар.')
      return null
    }
    return parsed
  }

  async function handleReceiving(event: FormEvent) {
    event.preventDefault()
    const parsed = validate()
    if (parsed === null) return
    if (effectiveExpiryDate < batchDate) {
      setError('Дата истечения не может быть раньше даты партии.')
      return
    }
    setBusy(true)
    try {
      const result = await createReceiving({
        product_id: Number(productId),
        quantity: parsed,
        batch_date: batchDate,
        expiry_date: effectiveExpiryDate,
      })
      setSuccess(
        `Принято ${formatQuantity(result.quantity_added)} шт. Партия №${result.batch.id}, остаток ${formatQuantity(result.batch.quantity)} шт.`,
      )
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function handleWriteOff(event: FormEvent) {
    event.preventDefault()
    const parsed = validate()
    if (parsed === null) return
    if (reason.trim() === '') {
      setError('Укажите причину списания.')
      return
    }
    setBusy(true)
    try {
      const result = await createWriteOff({
        product_id: Number(productId),
        quantity: parsed,
        reason: reason.trim(),
      })
      const batches = result.batches
        .map((batch) => `№${batch.batch_id} — ${formatQuantity(batch.quantity)} шт. (до ${formatDate(batch.expiry_date)})`)
        .join('; ')
      setSuccess(`Списано ${formatQuantity(result.quantity)} шт. Партии: ${batches}`)
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Card title="Складские операции">
        {loading && <Spinner label="Загрузка каталога…" />}
        <div className="field">
          <span className="field__label">Товар</span>
          <Select
            label="Товар"
            value={productId}
            fullWidth
            options={productOptions}
            onChange={(next) => {
              setProductId(next)
              setExpiryTouched(false)
            }}
          />
        </div>
        {barcodeParam !== null && (
          <p className="muted">Штрих-код: {barcodeParam}. Товар подобран автоматически.</p>
        )}
        {selectedProduct && (
          <p className="muted">
            <Link to={`/products/${selectedProduct.id}`}>Открыть карточку товара</Link> · Минимальный
            остаток: {formatQuantity(selectedProduct.min_stock)} шт.
          </p>
        )}
        <div className="tabs" role="tablist" aria-label="Операция">
          <button
            type="button"
            role="tab"
            aria-selected={operation === 'receiving'}
            className={`tab${operation === 'receiving' ? ' is-active' : ''}`}
            onClick={() => {
              setOperation('receiving')
              setError(null)
              setSuccess(null)
            }}
          >
            Приёмка
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={operation === 'write_off'}
            className={`tab${operation === 'write_off' ? ' is-active' : ''}`}
            onClick={() => {
              setOperation('write_off')
              setError(null)
              setSuccess(null)
            }}
          >
            Списание
          </button>
        </div>
        {operation === 'receiving' ? (
          <form className="stack" onSubmit={handleReceiving}>
            <label className="field">
              <span className="field__label">Количество, шт.</span>
              <Input
                type="number"
                min={1}
                step={1}
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                required
              />
            </label>
            <div className="form-grid">
              <label className="field">
                <span className="field__label">Дата партии</span>
                <Input
                  type="date"
                  value={batchDate}
                  onChange={(event) => setBatchDate(event.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span className="field__label">Годен до</span>
                <Input
                  type="date"
                  value={effectiveExpiryDate}
                  onChange={(event) => {
                    setExpiryDate(event.target.value)
                    setExpiryTouched(true)
                  }}
                  required
                />
              </label>
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? 'Отправка…' : 'Принять партию'}
            </Button>
          </form>
        ) : (
          <form className="stack" onSubmit={handleWriteOff}>
            <label className="field">
              <span className="field__label">Количество, шт.</span>
              <Input
                type="number"
                min={1}
                step={1}
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                required
              />
            </label>
            <div className="field">
              <span className="field__label">Причина</span>
              <Select
                label="Причина"
                value={reason}
                fullWidth
                options={reasonOptions}
                onChange={setReason}
              />
            </div>
            {!WRITE_OFF_REASONS.includes(reason) && (
              <label className="field">
                <span className="field__label">Уточнение причины</span>
                <Input value={reason} onChange={(event) => setReason(event.target.value)} required />
              </label>
            )}
            <Button type="submit" variant="danger" disabled={busy}>
              {busy ? 'Отправка…' : 'Списать'}
            </Button>
          </form>
        )}
        {error && <Alert type="error">{error}</Alert>}
        {success && <Alert type="success">{success}</Alert>}
      </Card>
      <Card title="Остатки по партиям">
        {productId === '' ? (
          <p className="muted">Выберите товар, чтобы увидеть его партии.</p>
        ) : (
          <>
            <p className="muted">Всего на складе: {formatQuantity(totalQuantity)} шт.</p>
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
                  {visibleInventory.map((item) => (
                    <tr key={item.id}>
                      <td>№{item.id}</td>
                      <td>{formatDate(item.batch_date)}</td>
                      <td>{formatDate(item.expiry_date)}</td>
                      <td>{formatQuantity(item.quantity)} шт.</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {visibleInventory.length === 0 && <p className="muted">Партий нет.</p>}
            </div>
          </>
        )}
      </Card>
    </>
  )
}
