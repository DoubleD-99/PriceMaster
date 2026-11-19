import { create } from 'zustand'

interface NetworkState {
  backendOnline: boolean | null
  setBackendOnline: (online: boolean) => void
}

export const useNetworkStore = create<NetworkState>((set) => ({
  backendOnline: null,
  setBackendOnline: (backendOnline) => set({ backendOnline }),
}))
