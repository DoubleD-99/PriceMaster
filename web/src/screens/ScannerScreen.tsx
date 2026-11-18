import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Html5QrcodeScanner } from 'html5-qrcode'
import { useNavigate } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'
import { lookupBarcode } from '../api/endpoints'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Spinner } from '../components/ui/Spinner'

const SCAN_DEBOUNCE_MS = 2_000

export function ScannerScreen() {
  const navigate = useNavigate()
  const scannerRef = useRef<HTMLDivElement>(null)
  const scannerInstance = useRef<Html5QrcodeScanner | null>(null)
  const lastScanRef = useRef(0)
  const [manualCode, setManualCode] = useState('')
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notFoundCode, setNotFoundCode] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const handleCode = useCallback(
    async (code: string) => {
      const value = code.trim()
      if (value === '') return
      const now = Date.now()
      if (now - lastScanRef.current < SCAN_DEBOUNCE_MS) return
      lastScanRef.current = now
      setBusy(true)
      setError(null)
      setNotFoundCode(null)
      try {
        const product = await lookupBarcode(value)
        navigate(`/products/${product.id}`)
      } catch (err) {
        setError(getErrorMessage(err))
        setNotFoundCode(value)
      } finally {
        setBusy(false)
      }
    },
    [navigate],
  )

  useEffect(() => {
    if (!scannerRef.current || scannerInstance.current !== null) return
    let scanner: Html5QrcodeScanner
    try {
      scanner = new Html5QrcodeScanner(
        scannerRef.current.id,
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
        },
        false,
      )
      scanner.render(
        (decodedText) => void handleCode(decodedText),
        () => undefined,
      )
      scannerInstance.current = scanner
    } catch (err) {
      const message = `Камера недоступна: ${getErrorMessage(err)}`
      queueMicrotask(() => setCameraError(message))
      return
    }

    return () => {
      scanner.clear().catch(() => undefined)
      scannerInstance.current = null
    }
  }, [handleCode])

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void handleCode(manualCode)
  }

  return (
    <Card title="Сканер штрих-кодов">
      <p className="muted">
        Наведите камеру на штрих-код или введите его вручную. После поиска откроется карточка товара.
      </p>
      <div id="scanner" ref={scannerRef} />
      {cameraError && <Alert type="warning">{cameraError}</Alert>}
      <form className="stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field__label">Штрих-код вручную</span>
          <Input
            value={manualCode}
            onChange={(event) => setManualCode(event.target.value)}
            placeholder="Например, 4600000000001"
            inputMode="numeric"
          />
        </label>
        <Button type="submit" disabled={busy || manualCode.trim() === ''}>
          {busy ? 'Поиск…' : 'Найти товар'}
        </Button>
      </form>
      {busy && <Spinner label="Поиск товара…" />}
      {error && <Alert type="error">{error}</Alert>}
      {notFoundCode !== null && (
        <Alert type="warning">
          Товар с кодом {notFoundCode} не найден. Можно оформить приёмку вручную.
          <Button
            variant="ghost"
            onClick={() => navigate(`/inventory?barcode=${encodeURIComponent(notFoundCode)}&operation=receiving`)}
          >
            оформить приёмку
          </Button>
        </Alert>
      )}
    </Card>
  )
}
