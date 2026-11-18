import { isAxiosError } from 'axios'

import type { ApiError } from '../types/api'

export function getErrorMessage(error: unknown): string {
  if (isAxiosError<ApiError>(error)) {
    const data = error.response?.data
    if (data !== undefined && typeof data.message === 'string' && data.message.length > 0) {
      return data.message
    }
    if (error.response?.status === 401) {
      return 'Сессия истекла. Войдите снова.'
    }
    if (error.response === undefined) {
      return 'Нет связи с сервером. Проверьте соединение.'
    }
    return 'Ошибка сервера. Попробуйте позже.'
  }
  if (error instanceof Error) return error.message
  return 'Неизвестная ошибка'
}

export function getErrorCode(error: unknown): string | null {
  if (!isAxiosError<ApiError>(error)) return null
  return error.response?.data?.error_code ?? null
}

export function getLoginErrorMessage(error: unknown): string {
  const code = getErrorCode(error)
  if (code === 'RATE_LIMITED') {
    return 'Слишком много попыток входа. Попробуйте позже.'
  }
  if (code === 'INVALID_ACCESS_KEY') {
    return 'Неверный ключ доступа.'
  }
  if (isAxiosError(error)) {
    const status = error.response?.status
    if (status === 401) {
      return 'Неверный ключ доступа.'
    }
    if (status !== undefined && status >= 500) {
      return 'Сервис входа временно недоступен. Попробуйте позже.'
    }
  }
  return getErrorMessage(error)
}
