import { Card } from '../components/ui/Card'

export function InventoryScreen() {
  return (
    <Card title="Склад">
      <p className="muted">Экран-заглушка для приёма/списания (SDD A.10). Реализация в Итерации 2–3.</p>
      <div className="stack">
        <form className="stack">
          <label className="field">
            <span className="field__label">Штрих-код</span>
            <input className="input" placeholder="Введите или отсканируйте ШК" />
          </label>
          <label className="field">
            <span className="field__label">Количество</span>
            <input className="input" type="number" defaultValue={1} min={1} />
          </label>
          <div className="row">
            <button className="btn btn--primary" type="button">
              Приём (заглушка)
            </button>
            <button className="btn btn--ghost" type="button">
              Списание (заглушка)
            </button>
          </div>
        </form>
      </div>
    </Card>
  )
}
