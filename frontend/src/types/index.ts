export interface ServiceStatus {
  running: boolean
  pid: number | null
  uptime_seconds: number | null
  service_url: string | null
  version: string
}

export type HealthStatus =
  | 'available'
  | 'not_found'
  | 'healthy'
  | 'unconfigured'
  | 'auth_error'
  | 'rate_limited'
  | 'network_error'
  | 'unknown'
  | 'checking'

export interface ProviderHealth {
  status: HealthStatus
  checked_at: number | null
}

export interface ModelInfo {
  name: string
  provider: string
  available: boolean
  health_status: HealthStatus
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
  health?: ProviderHealth
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
  fallback_chain?: string[]
}

export type Strategy = 'auto' | 'cost'

export interface FormulaWeights {
  quality: number
  cost: number
  reasoning: number
  creative: number
  context: number
}

export interface FormulaResponse {
  weights: Record<string, number>
}

export interface FormulaUpdateRequest {
  weights: Record<string, number>
}

export interface FormulaPreviewRequest {
  weights: Record<string, number>
  prompt: string
}

export interface FormulaPreviewModel {
  name: string
  score: number
}

export interface FormulaPreviewResponse {
  task_type: string
  difficulty: string
  models: FormulaPreviewModel[]
}

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
  level: string
}

export interface TokenStatsItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  reasoning_tokens: number
  cached_tokens: number
  request_count: number
}

export interface TokenStatsResponse {
  stats: TokenStatsItem[]
  total_prompt_tokens: number
  total_completion_tokens: number
  total_reasoning_tokens: number
  total_cached_tokens: number
  total_requests: number
}

export interface AnalyticsSummary {
  total_cost: number | null
  total_requests: number
  total_tokens: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_reasoning_tokens: number
  total_cached_tokens: number
  avg_daily_cost: number | null
  incomplete: boolean
}

export interface AnalyticsDailyItem {
  date: string
  cost: number
  requests: number
  tokens: number
  reasoning_tokens: number
  cached_tokens: number
}

export interface AnalyticsByModelItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  reasoning_tokens: number
  cached_tokens: number
  cost: number
  request_count: number
}

export interface AnalyticsTopModelItem {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  reasoning_tokens: number
  cached_tokens: number
  cost: number
  request_count: number
}

export interface PlaygroundRequest {
  mode: 'single' | 'compare'
  prompt: string
  models: string[]
}

export interface PlaygroundResult {
  model: string
  provider: string
  response: string
  latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  estimated_cost: number | null
  error: string | null
  routing_info: DryRunResult | null
}

export interface PlaygroundHistoryRecord {
  id: string
  mode: string
  prompt: string
  models: string[]
  results: PlaygroundResult[]
  created_at: number
}

export interface AlertCondition {
  metric: 'daily_cost' | 'daily_requests' | 'daily_tokens' | 'error_rate'
  operator: '>' | '<' | '>=' | '<='
  threshold: number
}

export interface AlertChannel {
  type: 'webhook' | 'log'
  url?: string
}

export interface AlertRule {
  id: string
  name: string
  enabled: boolean
  condition: AlertCondition
  severity: 'info' | 'warning' | 'critical'
  time_window: string
  channels: AlertChannel[]
  cooldown_minutes: number
}

export interface AlertHistoryItem {
  rule_id: string
  rule_name: string
  severity: string
  metric: string
  current_value: number
  threshold: number
  timestamp: number
  message: string
}

export interface RetryRecord {
  model: string
  status_code: number
  error: string | null
  timestamp: string
}

export interface RequestRoutingRecord {
  request_id: string
  timestamp: string
  original_model: string
  selected_model: string
  actual_model: string | null
  task_type: string | null
  difficulty: string | null
  strategy: string | null
  fallback_chain: string[]
  attempted_fallbacks: number | null
  did_fallback: boolean
  status_code: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  reasoning_tokens: number
  cached_tokens: number
  error_info: string | null
  retry_history?: RetryRecord[]
}
