import { create } from 'zustand'
import type {
  ServiceStatus,
  ModelInfo,
  ProviderInfo,
  DryRunResult,
  Strategy,
  ProviderUpdate,
  ModelOverrideState,
  LogState,
  LogSource,
  TokenStatsItem,
  AnalyticsSummary,
  AnalyticsDailyItem,
  AnalyticsByModelItem,
  AnalyticsTopModelItem,
  PlaygroundResult,
  PlaygroundHistoryRecord,
  PlaygroundRequest,
} from '../types'
import { api } from '../api/client'

interface DashboardState {
  // Data
  status: ServiceStatus | null
  models: ModelInfo[]
  providers: ProviderInfo[]
  dryRunResult: DryRunResult | null
  modelOverrides: Record<string, string[]>

  // UI
  isLoading: boolean
  isSavingProviders: boolean
  error: string | null
  toast: { message: string; type: 'success' | 'error' } | null
  modelsFilter: string
  modelsSort: { key: string; asc: boolean }

  // Model Override
  modelOverride: ModelOverrideState

  // Logs
  logs: LogState
  isLoadingLogs: boolean
  logError: string | null

  // Token Stats
  tokenStats: TokenStatsItem[]
  isLoadingTokenStats: boolean

  // Analytics
  analyticsSummary: AnalyticsSummary | null
  analyticsDaily: AnalyticsDailyItem[]
  analyticsByModel: AnalyticsByModelItem[]
  analyticsTopModels: AnalyticsTopModelItem[]
  isLoadingAnalytics: boolean
  analyticsError: string | null

  // Playground
  playgroundResults: PlaygroundResult[]
  playgroundHistory: PlaygroundHistoryRecord[]
  isLoadingPlayground: boolean
  playgroundError: string | null

  // Actions
  fetchAll: () => Promise<void>
  runDryRun: (prompt: string, strategy: Strategy) => Promise<void>
  stopService: () => Promise<void>
  saveProviders: (providers: Record<string, ProviderUpdate>) => Promise<void>
  setModelsFilter: (filter: string) => void
  setModelsSort: (key: string) => void
  clearError: () => void
  clearToast: () => void
  setModelOverride: (provider: string | null, model: string | null) => void
  clearModelOverride: () => void
  fetchLogs: (source?: LogSource) => Promise<void>
  setLogSource: (source: LogSource) => void
  clearLogError: () => void
  fetchTokenStats: () => Promise<void>
  fetchAnalytics: (days?: number) => Promise<void>
  runPlayground: (request: PlaygroundRequest) => Promise<void>
  fetchPlaygroundHistory: () => Promise<void>
  deletePlaygroundHistory: (id: string) => Promise<void>
  clearPlaygroundError: () => void
}

const STORAGE_KEY = 'smart-router-model-override'

function loadOverrideFromStorage(): ModelOverrideState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object') {
        return {
          provider: parsed.provider || null,
          model: parsed.model || null,
          enabled: !!parsed.enabled,
        }
      }
    }
  } catch {
    // ignore parse errors
  }
  return { provider: null, model: null, enabled: false }
}

function saveOverrideToStorage(state: ModelOverrideState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore storage errors
  }
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  status: null,
  models: [],
  providers: [],
  dryRunResult: null,
  modelOverrides: {},
  isLoading: false,
  isSavingProviders: false,
  error: null,
  toast: null,
  modelsFilter: '',
  modelsSort: { key: 'name', asc: true },
  modelOverride: loadOverrideFromStorage(),
  logs: { lines: [], offset: 0, total_size: 0, source: 'service' as LogSource },
  isLoadingLogs: false,
  logError: null,
  tokenStats: [],
  isLoadingTokenStats: false,
  analyticsSummary: null,
  analyticsDaily: [],
  analyticsByModel: [],
  analyticsTopModels: [],
  isLoadingAnalytics: false,
  analyticsError: null,

  // Playground
  playgroundResults: [],
  playgroundHistory: [],
  isLoadingPlayground: false,
  playgroundError: null,

  fetchAll: async () => {
    set({ isLoading: true, error: null })
    try {
      const [status, modelsRes, providersRes, overridesRes, tokenStatsRes] = await Promise.all([
        api.getStatus(),
        api.getModels(),
        api.getProviders(),
        api.getModelOverrides(),
        api.getTokenStats(),
      ])
      set({
        status,
        models: modelsRes.models,
        providers: providersRes.providers,
        modelOverrides: overridesRes.overrides,
        tokenStats: tokenStatsRes.stats,
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

  setModelOverride: (provider: string | null, model: string | null) => {
    const state = { provider, model, enabled: !!(provider && model) }
    saveOverrideToStorage(state)
    set({ modelOverride: state })
  },

  clearModelOverride: () => {
    const state = { provider: null, model: null, enabled: false }
    saveOverrideToStorage(state)
    set({ modelOverride: state })
  },

  fetchLogs: async (source?: LogSource) => {
    const currentSource = source || get().logs.source
    const currentOffset = source ? 0 : get().logs.offset

    set({ isLoadingLogs: true, logError: null })
    try {
      const result = await api.getLogs(currentSource, currentOffset, 500)
      const existingLines = source ? [] : get().logs.lines
      set({
        logs: {
          lines: [...existingLines, ...result.lines],
          offset: result.offset,
          total_size: result.total_size,
          source: currentSource,
        },
        isLoadingLogs: false,
      })
    } catch (err) {
      set({ logError: (err as Error).message, isLoadingLogs: false })
    }
  },

  setLogSource: (source: LogSource) => {
    set({
      logs: { lines: [], offset: 0, total_size: 0, source },
      logError: null,
    })
  },

  clearLogError: () => set({ logError: null }),

  fetchTokenStats: async () => {
    set({ isLoadingTokenStats: true })
    try {
      const result = await api.getTokenStats()
      set({ tokenStats: result.stats, isLoadingTokenStats: false })
    } catch (err) {
      set({ error: (err as Error).message, isLoadingTokenStats: false })
    }
  },

  fetchAnalytics: async (days = 7) => {
    set({ isLoadingAnalytics: true, analyticsError: null })
    try {
      const [summary, daily, byModel, topModels] = await Promise.all([
        api.getAnalyticsSummary(days),
        api.getAnalyticsDaily(days),
        api.getAnalyticsByModel(days),
        api.getAnalyticsTopModels(10, days),
      ])
      set({
        analyticsSummary: summary,
        analyticsDaily: daily,
        analyticsByModel: byModel,
        analyticsTopModels: topModels,
        isLoadingAnalytics: false,
      })
    } catch (err) {
      set({ analyticsError: (err as Error).message, isLoadingAnalytics: false })
    }
  },

  runPlayground: async (request: PlaygroundRequest) => {
    set({ isLoadingPlayground: true, playgroundError: null })
    try {
      const result = await api.postPlayground(request)
      set({ playgroundResults: result.results, isLoadingPlayground: false })
    } catch (err) {
      set({ playgroundError: (err as Error).message, isLoadingPlayground: false })
    }
  },

  fetchPlaygroundHistory: async () => {
    try {
      const result = await api.getPlaygroundHistory()
      set({ playgroundHistory: result.history })
    } catch {
      // 历史记录加载失败不设置错误
    }
  },

  deletePlaygroundHistory: async (id: string) => {
    try {
      await api.deletePlaygroundHistory(id)
      set((state) => ({
        playgroundHistory: state.playgroundHistory.filter((h) => h.id !== id),
      }))
    } catch (err) {
      set({ playgroundError: (err as Error).message })
    }
  },

  clearPlaygroundError: () => set({ playgroundError: null }),
}))
