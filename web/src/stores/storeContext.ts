import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

interface StoreContextState {
  storeId: number | null
  setStoreId: (id: number | null) => void
}

// Выбранный магазин сохраняется в localStorage, чтобы не сбрасывался
// при перезагрузке (SDD §4.1); уходит в заголовке X-Store-ID.
export const useStoreContext = create<StoreContextState>()(
  persist(
    (set) => ({
      storeId: null,
      setStoreId: (storeId) => set({ storeId }),
    }),
    {
      name: 'pricemaster-store',
      storage: createJSONStorage(() => localStorage),
    },
  ),
)
