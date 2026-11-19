import { describe, expect, it } from 'vitest'

import { getLoginErrorMessage } from './errors'

describe('getLoginErrorMessage', () => {
  it('explains an invalid access key', () => {
    const error = {
      isAxiosError: true,
      response: {
        status: 401,
        data: {
          error_code: 'INVALID_ACCESS_KEY',
          message: 'Неверный access_key',
          details: {},
        },
      },
    }

    expect(getLoginErrorMessage(error)).toBe('Неверный ключ доступа.')
  })

  it('does not show a raw internal server error', () => {
    const error = {
      isAxiosError: true,
      response: {
        status: 500,
        data: {
          error_code: 'INTERNAL_ERROR',
          message: 'Внутренняя ошибка сервера',
          details: {},
        },
      },
    }

    expect(getLoginErrorMessage(error)).toBe(
      'Сервис входа временно недоступен. Попробуйте позже.',
    )
  })
})
