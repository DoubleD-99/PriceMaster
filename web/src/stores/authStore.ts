import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  login: (token: string) => void
  logout: () => void
}

// Токен живёт в sessionStorage: переживает перезагрузку вкладки,
// но не шарится между вкладками и очищается при закрытии (SDD §4.1).
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      login: (token) => set({ token }),
      logout: () => set({ token: null }),
    }),
    {
      name: 'pricemaster-auth',
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
)
