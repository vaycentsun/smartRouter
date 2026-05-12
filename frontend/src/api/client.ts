import axios from 'axios'
import type {
  ServiceStatus,
  ModelsResponse,
  ProvidersResponse,
  DryRunRequest,
  DryRunResult,
  ProviderUpdate,
  ModelOverrideInfo,
  LogsResponse,
  LogSource,
  TokenStatsResponse,
  AnalyticsSummary,
  AnalyticsDailyItem,
  AnalyticsByModelItem,
  AnalyticsTopModelItem,
  PlaygroundRequest,
  PlaygroundResult,
  PlaygroundHistoryRecord,
  AlertRule,
  AlertHistoryItem,
  HealthStatus,
  FormulaResponse,
  FormulaUpdateRequest,
  FormulaPreviewRequest,
  FormulaPreviewResponse,
  RequestRoutingRecord,
  ErrorStatsResponse,
} from '../types'

export interface AlertTestResult {
  triggered: boolean
  triggers: Array<{
    rule_id: string
    rule_name: string
    severity: string
    metric: string
    current_value: number
    threshold: number
    message: string
  }>
}

const client = axios.create({
  baseURL: '',
  timeout: 10000,
})

client.interceptors.request.use((config) => {
  const overrideStr = localStorage.getItem('smart-router-model-override')
  if (overrideStr) {
    try {
      const override = JSON.parse(overrideStr)
      if (override.enabled && override.provider && override.model) {
        config.headers['X-Smart-Router-Override-Provider'] = override.provider
        config.headers['X-Smart-Router-Override-Model'] = override.model
      }
    } catch {}
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export const api = {
  getStatus: () => client.get<ServiceStatus>('/api/status').then((r) => r.data),
  getModels: () => client.get<ModelsResponse>('/api/models').then((r) => r.data),
  getProviders: () => client.get<ProvidersResponse>('/api/providers').then((r) => r.data),
  checkProviderHealth: (providerName: string) =>
    client.get<{
      provider: string
      status: HealthStatus
      models: string[]
      checked_at: number
      error: string | null
    }>(`/api/providers/${providerName}/health`).then((r) => r.data),
  getModelOverrides: () => client.get<ModelOverrideInfo>('/api/model-overrides').then((r) => r.data),
  getModelOverride: () => client.get<{ provider: string | null; model: string | null; enabled: boolean }>('/api/model-override').then((r) => r.data),
  setModelOverride: (provider: string, model: string) =>
    client.post<{ provider: string; model: string; enabled: boolean }>('/api/model-override', { provider, model }).then((r) => r.data),
  clearModelOverride: () => client.delete<{ provider: null; model: null; enabled: false }>('/api/model-override').then((r) => r.data),
  dryRun: (data: DryRunRequest) =>
    client.post<DryRunResult>('/api/dry-run', data).then((r) => r.data),
  stopService: () => client.post('/api/stop').then((r) => r.data),
  putProviders: (data: Record<string, ProviderUpdate>) =>
    client.put<{ success: boolean; errors?: string[] }>('/api/providers', { providers: data }).then((r) => r.data),
  getLogs: (source: LogSource, offset: number, limit?: number, level?: string) =>
    client.get<LogsResponse>('/api/logs', { params: { source, offset, limit, level } }).then((r) => r.data),
  getTokenStats: () =>
    client.get<TokenStatsResponse>('/api/token-stats').then((r) => r.data),
  getAnalyticsSummary: (days = 7) =>
    client.get<AnalyticsSummary>('/api/analytics/summary', { params: { days } }).then((r) => r.data),
  getAnalyticsDaily: (days = 7) =>
    client.get<AnalyticsDailyItem[]>('/api/analytics/daily', { params: { days } }).then((r) => r.data),
  getAnalyticsByModel: (days = 7) =>
    client.get<AnalyticsByModelItem[]>('/api/analytics/by-model', { params: { days } }).then((r) => r.data),
  getAnalyticsTopModels: (limit = 10, days = 7) =>
    client.get<AnalyticsTopModelItem[]>('/api/analytics/top-models', { params: { limit, days } }).then((r) => r.data),
  getRecentRequests: (limit = 50) =>
    client.get<{ requests: RequestRoutingRecord[] }>('/api/analytics/recent-requests', { params: { limit } }).then((r) => r.data),
  getErrorStats: (days = 7) =>
    client.get<ErrorStatsResponse>('/api/analytics/error-stats', { params: { days } }).then((r) => r.data),
  postPlayground: (data: PlaygroundRequest) =>
    client.post<{ results: PlaygroundResult[] }>('/api/playground/completions', data).then((r) => r.data),
  getPlaygroundHistory: () =>
    client.get<{ history: PlaygroundHistoryRecord[] }>('/api/playground/history').then((r) => r.data),
  deletePlaygroundHistory: (id: string) =>
    client.delete<{ success: boolean }>(`/api/playground/history/${id}`).then((r) => r.data),
  // Alerts
  getAlertRules: () =>
    client.get<{ rules: AlertRule[] }>('/api/alerts/rules').then((r) => r.data),
  createAlertRule: (data: AlertRule) =>
    client.post<{ success: boolean; rule: AlertRule }>('/api/alerts/rules', data).then((r) => r.data),
  updateAlertRule: (id: string, data: Partial<AlertRule>) =>
    client.put<{ success: boolean; rule: AlertRule }>(`/api/alerts/rules/${id}`, data).then((r) => r.data),
  deleteAlertRule: (id: string) =>
    client.delete<{ success: boolean }>(`/api/alerts/rules/${id}`).then((r) => r.data),
  getAlertHistory: (limit = 50) =>
    client.get<{ history: AlertHistoryItem[] }>('/api/alerts/history', { params: { limit } }).then((r) => r.data),
  testAlertRule: (data: AlertRule) =>
    client.post<AlertTestResult>('/api/alerts/test', data).then((r) => r.data),
  // Formula
  getFormula: () =>
    client.get<FormulaResponse>('/api/formula').then((r) => r.data),
  updateFormula: (data: FormulaUpdateRequest) =>
    client.put<{ success: boolean; errors?: string[] }>('/api/formula', data).then((r) => r.data),
  previewFormula: (data: FormulaPreviewRequest) =>
    client.post<FormulaPreviewResponse>('/api/formula/preview', data).then((r) => r.data),
}
