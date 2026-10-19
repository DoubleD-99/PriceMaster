import { useEffect, useRef } from 'react'
import { Html5QrcodeScanner } from 'html5-qrcode'
import { Card } from '../components/ui/Card'

export function ScannerScreen() {
  const scannerRef = useRef<HTMLDivElement>(null)
  const scannerInstance = useRef<Html5QrcodeScanner | null>(null)

  useEffect(() => {
    if (!scannerRef.current) return
    if (scannerInstance.current) return

    const scanner = new Html5QrcodeScanner(
      scannerRef.current.id,
      {
        fps: 10,
        qrbox: { width: 250, height: 250 },
      },
      false,
    )

    scanner.render(
      (decodedText) => {
        console.info('Barcode detected:', decodedText)
        alert(`Штрих-код обнаружен: ${decodedText}`)
      },
      () => {
        // ignore scan errors
      },
    )
    scannerInstance.current = scanner

    return () => {
      scanner.clear().catch(() => undefined)
      scannerInstance.current = null
    }
  }, [])

  return (
    <Card title="Сканер штрих-кодов">
      <p className="muted">Заглушка под html5-qrcode (SDD A.10). Интеграция с приёмкой/списанием — позже.</p>
      <div id="scanner" ref={scannerRef} />
    </Card>
  )
}
