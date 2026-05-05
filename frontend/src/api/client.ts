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
} from '../types'

const client = axios.create({
  baseURL: '',
  timeout: 10000,
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
  getModelOverrides: () => client.get<ModelOverrideInfo>('/api/model-overrides').then((r) => r.data),
  dryRun: (data: DryRunRequest) =>
    client.post<DryRunResult>('/api/dry-run', data).then((r) => r.data),
  stopService: () => client.post('/api/stop').then((r) => r.data),
  putProviders: (data: Record<string, ProviderUpdate>) =>
    client.put<{ success: boolean; errors?: string[] }>('/api/providers', { providers: data }).then((r) => r.data),
  getLogs: (source: LogSource, offset: number, limit?: number) =>
    client.get<LogsResponse>('/api/logs', { params: { source, offset, limit } }).then((r) => r.data),
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
  postPlayground: (data: PlaygroundRequest) =>
    client.post<{ results: PlaygroundResult[] }>('/api/playground/completions', data).then((r) => r.data),
  getPlaygroundHistory: () =>
    client.get<{ history: PlaygroundHistoryRecord[] }>('/api/playground/history').then((r) => r.data),
  deletePlaygroundHistory: (id: string) =>
    client.delete<{ success: boolean }>(`/api/playground/history/${id}`).then((r) => r.data),
}
