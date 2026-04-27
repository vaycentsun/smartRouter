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
}

export interface ProvidersResponse {
  providers: ProviderInfo[]
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
