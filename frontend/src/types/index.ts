export interface ServiceStatus {
  running: boolean
  pid: number | null
  uptime_seconds: number | null
  service_url: string | null
  version: string
}

export interface ModelInfo {
  name: string
  provider: string
  available: boolean
  quality: number
  cost: number
  context: number
  supported_tasks: string[]
}

export interface ModelsResponse {
  models: ModelInfo[]
  total: number
  available: number
  unavailable: number
}

export interface ProviderInfo {
  name: string
  api_base: string
  timeout: number
  key_type: string
  has_key: boolean
  masked_key?: string
}

export interface ProvidersResponse {
  providers: ProviderInfo[]
}

export interface ProviderUpdate {
  api_base?: string
  api_key?: string
  timeout?: number
}

export interface DryRunRequest {
  prompt: string
  strategy: string
}

export interface DryRunResult {
  task_type: string
  task_confidence: number
  difficulty: string
  difficulty_confidence: number
  selected_model: string
  strategy: string
  score: number
  reason: string
  error?: string
}

export type Strategy = 'auto' | 'quality' | 'cost' | 'speed' | 'balanced'

export interface ModelOverrideInfo {
  overrides: Record<string, string[]>
}

export interface ModelOverrideState {
  provider: string | null
  model: string | null
  enabled: boolean
}

export interface LogsResponse {
  lines: string[]
  offset: number
  total_size: number
}

export type LogSource = 'service' | 'dashboard'

export interface LogState {
  lines: string[]
  offset: number
  total_size: number
  source: LogSource
}

export interface TokenStatsItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  request_count: number
}

export interface TokenStatsResponse {
  stats: TokenStatsItem[]
  total_prompt_tokens: number
  total_completion_tokens: number
  total_requests: number
}

export interface AnalyticsSummary {
  total_cost: number | null
  total_requests: number
  total_tokens: number
  avg_daily_cost: number | null
  incomplete: boolean
}

export interface AnalyticsDailyItem {
  date: string
  cost: number
  requests: number
  tokens: number
}

export interface AnalyticsByModelItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  cost: number
  request_count: number
}

export interface AnalyticsTopModelItem {
  model: string
  total_tokens: number
  cost: number
  request_count: number
}
