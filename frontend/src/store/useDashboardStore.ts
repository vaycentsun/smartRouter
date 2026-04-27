import { create } from 'zustand'
import type {
  ServiceStatus,
  ModelInfo,
  ProviderInfo,
  DryRunResult,
  Strategy,
  ProviderUpdate,
} from '../types'
import { api } from '../api/client'

interface DashboardState {
  // Data
  status: ServiceStatus | null
  models: ModelInfo[]
  providers: ProviderInfo[]
  dryRunResult: DryRunResult | null

  // UI
  isLoading: boolean
  isSavingProviders: boolean
  error: string | null
  toast: { message: string; type: 'success' | 'error' } | null
  modelsFilter: string
  modelsSort: { key: string; asc: boolean }

  // Actions
  fetchAll: () => Promise<void>
  runDryRun: (prompt: string, strategy: Strategy) => Promise<void>
  stopService: () => Promise<void>
  saveProviders: (providers: Record<string, ProviderUpdate>) => Promise<void>
  setModelsFilter: (filter: string) => void
  setModelsSort: (key: string) => void
  clearError: () => void
  clearToast: () => void
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  status: null,
  models: [],
  providers: [],
  dryRunResult: null,
  isLoading: false,
  isSavingProviders: false,
  error: null,
  toast: null,
  modelsFilter: '',
  modelsSort: { key: 'name', asc: true },

  fetchAll: async () => {
    set({ isLoading: true, error: null })
    try {
      const [status, modelsRes, providersRes] = await Promise.all([
        api.getStatus(),
        api.getModels(),
        api.getProviders(),
      ])
      set({
        status,
        models: modelsRes.models,
        providers: providersRes.providers,
        isLoading: false,
      })
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false })
    }
  },

  runDryRun: async (prompt: string, strategy: Strategy) => {
    set({ isLoading: true, error: null })
    try {
      const result = await api.dryRun({ prompt, strategy })
      set({ dryRunResult: result, isLoading: false })
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false })
    }
  },

  stopService: async () => {
    set({ isLoading: true, error: null })
    try {
      await api.stopService()
      await get().fetchAll()
      set({ isLoading: false })
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false })
    }
  },

  saveProviders: async (providers: Record<string, ProviderUpdate>) => {
    set({ isSavingProviders: true, error: null, toast: null })
    try {
      const result = await api.putProviders(providers)
      if (result.success) {
        set({ toast: { message: 'Provider 配置已保存', type: 'success' } })
        await get().fetchAll()
      } else {
        set({ error: result.errors?.join('; ') || '保存失败', toast: { message: '保存失败', type: 'error' } })
      }
    } catch (err) {
      const msg = (err as Error).message
      set({ error: msg, toast: { message: msg, type: 'error' } })
    } finally {
      set({ isSavingProviders: false })
    }
  },

  setModelsFilter: (filter: string) => set({ modelsFilter: filter }),

  setModelsSort: (key: string) => {
    const current = get().modelsSort
    if (current.key === key) {
      set({ modelsSort: { key, asc: !current.asc } })
    } else {
      set({ modelsSort: { key, asc: true } })
    }
  },

  clearError: () => set({ error: null }),
  clearToast: () => set({ toast: null }),
}))
