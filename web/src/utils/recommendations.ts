import { formatMoney, formatQuantity, toNumber } from './format'
import type { Recommendation, RecommendationAction, RecommendationStatus } from '../types/api'

export const ACTION_LABELS: Record<RecommendationAction, string> = {
  price_change: 'Изменение цены',
  reorder: 'Пополнение',
  write_off: 'Списание',
}

export const STATUS_LABELS: Record<RecommendationStatus, string> = {
  pending: 'Ожидает',
  accepted: 'Принята',
  rejected: 'Отклонена',
}

export function formatRecommendationValue(recommendation: Recommendation): string {
  if (recommendation.action_type === 'price_change') {
    return `${formatMoney(recommendation.recommended_value)} ₽`
  }
  return `${formatQuantity(toNumber(recommendation.recommended_value))} шт.`
}
