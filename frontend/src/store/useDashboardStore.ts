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
  AlertRule,
  AlertHistoryItem,
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

  // Alerts
  alertRules: AlertRule[]
  alertHistory: AlertHistoryItem[]
  isLoadingAlerts: boolean
  alertsError: string | null

  // Health Check
  isCheckingHealth: Record<string, boolean>

  // Actions
  fetchAll: () => Promise<void>
  checkProviderHealth: (providerName: string) => Promise<void>
  runDryRun: (prompt: string, strategy: Strategy) => Promise<void>
  stopService: () => Promise<void>
  saveProviders: (providers: Record<string, ProviderUpdate>) => Promise<void>
  setModelsFilter: (filter: string) => void
  setModelsSort: (key: string) => void
  clearError: () => void
  clearToast: () => void
  setModelOverride: (provider: string | null, model: string | null) => Promise<void>
  clearModelOverride: () => Promise<void>
  fetchLogs: (source?: LogSource) => Promise<void>
  setLogSource: (source: LogSource) => void
  clearLogError: () => void
  fetchTokenStats: () => Promise<void>
  fetchAnalytics: (days?: number) => Promise<void>
  runPlayground: (request: PlaygroundRequest) => Promise<void>
  fetchPlaygroundHistory: () => Promise<void>
  deletePlaygroundHistory: (id: string) => Promise<void>
  clearPlaygroundError: () => void
  fetchAlertRules: () => Promise<void>
  createAlertRule: (rule: AlertRule) => Promise<void>
  updateAlertRule: (id: string, rule: Partial<AlertRule>) => Promise<void>
  deleteAlertRule: (id: string) => Promise<void>
  fetchAlertHistory: () => Promise<void>
  testAlertRule: (rule: AlertRule) => Promise<{ triggered: boolean; triggers: Array<Pick<AlertHistoryItem, 'rule_id' | 'rule_name' | 'severity' | 'metric' | 'current_value' | 'threshold' | 'message'>> } | null>
  clearAlertsError: () => void
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

  // Alerts
  alertRules: [],
  alertHistory: [],
  isLoadingAlerts: false,
  alertsError: null,

  // Health Check
  isCheckingHealth: {},

  fetchAll: async () => {
    set({ isLoading: true, error: null })
    try {
      const [status, modelsRes, providersRes, overridesRes, tokenStatsRes, overrideState] = await Promise.all([
        api.getStatus(),
        api.getModels(),
        api.getProviders(),
        api.getModelOverrides(),
        api.getTokenStats(),
        api.getModelOverride(),
      ])
      set({
        status,
        models: modelsRes.models,
        providers: providersRes.providers,
        modelOverrides: overridesRes.overrides,
        tokenStats: tokenStatsRes.stats,
        modelOverride: {
          provider: overrideState.provider || null,
          model: overrideState.model || null,
          enabled: overrideState.enabled,
        },
        isLoading: false,
      })
      // 同步到 localStorage
      saveOverrideToStorage({
        provider: overrideState.provider || null,
        model: overrideState.model || null,
        enabled: overrideState.enabled,
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

  setModelOverride: async (provider: string | null, model: string | null) => {
    const enabled = !!(provider && model)
    if (!enabled) {
      const state = { provider: null, model: null, enabled: false }
      saveOverrideToStorage(state)
      set({ modelOverride: state })
      try {
        await api.clearModelOverride()
      } catch {
        // ignore
      }
      return
    }
    try {
      const result = await api.setModelOverride(provider, model)
      const state = {
        provider: result.provider || null,
        model: result.model || null,
        enabled: result.enabled,
      }
      saveOverrideToStorage(state)
      set({ modelOverride: state })
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },

  clearModelOverride: async () => {
    const state = { provider: null, model: null, enabled: false }
    saveOverrideToStorage(state)
    set({ modelOverride: state })
    try {
      await api.clearModelOverride()
    } catch {
      // ignore
    }
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

  fetchAlertRules: async () => {
    set({ isLoadingAlerts: true, alertsError: null })
    try {
      const result = await api.getAlertRules()
      set({ alertRules: result.rules, isLoadingAlerts: false })
    } catch (err) {
      set({ alertsError: (err as Error).message, isLoadingAlerts: false })
    }
  },

  createAlertRule: async (rule: AlertRule) => {
    set({ isLoadingAlerts: true, alertsError: null })
    try {
      await api.createAlertRule(rule)
      await get().fetchAlertRules()
      set({ toast: { message: '告警规则已创建', type: 'success' }, isLoadingAlerts: false })
    } catch (err) {
      set({ alertsError: (err as Error).message, isLoadingAlerts: false })
    }
  },

  updateAlertRule: async (id: string, rule: Partial<AlertRule>) => {
    set({ isLoadingAlerts: true, alertsError: null })
    try {
      await api.updateAlertRule(id, rule)
      await get().fetchAlertRules()
      set({ toast: { message: '告警规则已更新', type: 'success' }, isLoadingAlerts: false })
    } catch (err) {
      set({ alertsError: (err as Error).message, isLoadingAlerts: false })
    }
  },

  deleteAlertRule: async (id: string) => {
    set({ isLoadingAlerts: true, alertsError: null })
    try {
      await api.deleteAlertRule(id)
      await get().fetchAlertRules()
      set({ toast: { message: '告警规则已删除', type: 'success' }, isLoadingAlerts: false })
    } catch (err) {
      set({ alertsError: (err as Error).message, isLoadingAlerts: false })
    }
  },

  fetchAlertHistory: async () => {
    try {
      const result = await api.getAlertHistory(50)
      set({ alertHistory: result.history })
    } catch {
      // 历史记录加载失败不设置错误
    }
  },

  testAlertRule: async (rule: AlertRule) => {
    try {
      const result = await api.testAlertRule(rule)
      return result
    } catch (err) {
      set({ alertsError: (err as Error).message })
      return null
    }
  },

  clearAlertsError: () => set({ alertsError: null }),

  checkProviderHealth: async (providerName: string) => {
    set((state) => ({
      isCheckingHealth: { ...state.isCheckingHealth, [providerName]: true },
    }))
    try {
      const result = await api.checkProviderHealth(providerName)

      // 更新 provider 的 health 字段
      set((state) => ({
        providers: state.providers.map((p) =>
          p.name === providerName
            ? { ...p, health: { status: result.status, checked_at: result.checked_at } }
            : p
        ),
        isCheckingHealth: { ...state.isCheckingHealth, [providerName]: false },
      }))

      // 同步刷新 models 列表以获取最新的 health_status
      const modelsRes = await api.getModels()
      set({ models: modelsRes.models })
    } catch (err) {
      set((state) => ({
        error: (err as Error).message,
        isCheckingHealth: { ...state.isCheckingHealth, [providerName]: false },
      }))
    }
  },
}))
