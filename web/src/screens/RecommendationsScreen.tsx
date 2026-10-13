import { Card } from '../components/ui/Card'

export function RecommendationsScreen() {
  return (
    <Card title="Рекомендации по ценам">
      <p className="muted">Таблица рекомендаций + фильтры (заглушка). Реализация согласно SDD B.2–B.3.</p>
      <div className="stack">
        <div className="row">
          <label className="field">
            <span className="field__label">Статус</span>
            <select className="input">
              <option value="">Все</option>
              <option value="NEW">Новые</option>
              <option value="ACCEPTED">Принятые</option>
              <option value="REJECTED">Отклонённые</option>
            </select>
          </label>
        </div>
        <p className="muted">Данных пока нет (seed + расчёты появятся позже)</p>
      </div>
    </Card>
  )
}
