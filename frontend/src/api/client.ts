import axios from 'axios'
import type {
  ServiceStatus,
  ModelsResponse,
  ProvidersResponse,
  DryRunRequest,
  DryRunResult,
  ProviderUpdate,
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
  dryRun: (data: DryRunRequest) =>
    client.post<DryRunResult>('/api/dry-run', data).then((r) => r.data),
  stopService: () => client.post('/api/stop').then((r) => r.data),
  putProviders: (data: Record<string, ProviderUpdate>) =>
    client.put<{ success: boolean; errors?: string[] }>('/api/providers', { providers: data }).then((r) => r.data),
}
