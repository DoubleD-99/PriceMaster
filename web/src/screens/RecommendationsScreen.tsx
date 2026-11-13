import { Card } from '../components/ui/Card'

export function RecommendationsScreen() {
  return (
    <Card title="Рекомендации">
      <p className="muted">Таблица рекомендаций + фильтры. Контракт — SDD §6.4.</p>
      <div className="stack">
        <div className="row">
          <label className="field">
            <span className="field__label">Статус</span>
            <select className="input">
              <option value="">Все</option>
              <option value="pending">Ожидают</option>
              <option value="accepted">Принятые</option>
              <option value="rejected">Отклонённые</option>
            </select>
          </label>
        </div>
        <p className="muted">Подключение к GET /recommendations — следующий шаг.</p>
      </div>
    </Card>
  )
}
