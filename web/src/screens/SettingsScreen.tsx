import { Card } from '../components/ui/Card'
import { useStoreContext } from '../stores/storeContext'

export function SettingsScreen() {
  const storeId = useStoreContext((state) => state.storeId)
  const setStoreId = useStoreContext((state) => state.setStoreId)

  return (
    <Card title="Настройки">
      <p className="muted">Базовые настройки (заглушка). Выбор магазина для контекста запросов.</p>
      <div className="stack">
        <label className="field">
          <span className="field__label">Текущий магазин (ID)</span>
          <input
            className="input"
            type="number"
            value={storeId ?? ''}
            onChange={(e) => setStoreId(e.target.value ? Number(e.target.value) : null)}
            placeholder="Укажите ID магазина"
          />
        </label>
        <p className="muted">После выбора магазина заголовки запросов будут содержать X-Store-ID.</p>
      </div>
    </Card>
  )
}
