import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { api } from '../api/client'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    api: {
      getStatus: vi.fn(),
      getModels: vi.fn(),
      getProviders: vi.fn(),
      dryRun: vi.fn(),
      stopService: vi.fn(),
      putProviders: vi.fn(),
    },
  }
})

import { useDashboardStore } from './useDashboardStore'

describe('useDashboardStore', () => {
  beforeEach(() => {
    useDashboardStore.setState({
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
    })
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const state = useDashboardStore.getState()
    expect(state.status).toBeNull()
    expect(state.models).toEqual([])
    expect(state.providers).toEqual([])
    expect(state.dryRunResult).toBeNull()
    expect(state.isLoading).toBe(false)
    expect(state.isSavingProviders).toBe(false)
    expect(state.error).toBeNull()
    expect(state.toast).toBeNull()
    expect(state.modelsFilter).toBe('')
    expect(state.modelsSort).toEqual({ key: 'name', asc: true })
  })

  describe('fetchAll', () => {
    it('sets loading, fetches data, and updates state on success', async () => {
      const status = { running: true, pid: 123, uptime_seconds: 60, service_url: 'http://localhost:4000', version: '1.0.0' }
      const modelsRes = { models: [{ name: 'gpt-4', provider: 'openai', available: true, quality: 9, cost: 3, context: 8192, supported_tasks: ['chat'] }], total: 1, available: 1, unavailable: 0 }
      const providersRes = { providers: [{ name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true }] }

      ;(api.getStatus as Mock).mockResolvedValue(status)
      ;(api.getModels as Mock).mockResolvedValue(modelsRes)
      ;(api.getProviders as Mock).mockResolvedValue(providersRes)

      await useDashboardStore.getState().fetchAll()

      const state = useDashboardStore.getState()
      expect(state.status).toEqual(status)
      expect(state.models).toEqual(modelsRes.models)
      expect(state.providers).toEqual(providersRes.providers)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('sets error on failure', async () => {
      ;(api.getStatus as Mock).mockRejectedValue(new Error('network error'))

      await useDashboardStore.getState().fetchAll()

      const state = useDashboardStore.getState()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBe('network error')
    })
  })

  describe('runDryRun', () => {
    it('sets result on success', async () => {
      const result = { task_type: 'chat', task_confidence: 0.9, difficulty: 'easy', difficulty_confidence: 0.8, selected_model: 'gpt-4', strategy: 'auto', score: 8.5, reason: 'fast' }
      ;(api.dryRun as Mock).mockResolvedValue(result)

      await useDashboardStore.getState().runDryRun('hello', 'auto')

      const state = useDashboardStore.getState()
      expect(state.dryRunResult).toEqual(result)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('sets error on failure', async () => {
      ;(api.dryRun as Mock).mockRejectedValue(new Error('bad request'))

      await useDashboardStore.getState().runDryRun('hello', 'auto')

      const state = useDashboardStore.getState()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBe('bad request')
    })
  })

  describe('stopService', () => {
    it('calls stopService then fetchAll on success', async () => {
      ;(api.stopService as Mock).mockResolvedValue({})
      ;(api.getStatus as Mock).mockResolvedValue({ running: false, pid: null, uptime_seconds: null, service_url: null, version: '1.0.0' })
      ;(api.getModels as Mock).mockResolvedValue({ models: [], total: 0, available: 0, unavailable: 0 })
      ;(api.getProviders as Mock).mockResolvedValue({ providers: [] })

      await useDashboardStore.getState().stopService()

      const state = useDashboardStore.getState()
      expect(state.isLoading).toBe(false)
      expect(api.stopService).toHaveBeenCalled()
      expect(api.getStatus).toHaveBeenCalled()
    })

    it('sets error on failure', async () => {
      ;(api.stopService as Mock).mockRejectedValue(new Error('stop failed'))

      await useDashboardStore.getState().stopService()

      const state = useDashboardStore.getState()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBe('stop failed')
    })
  })

  describe('saveProviders', () => {
    it('shows success toast and refreshes on success', async () => {
      ;(api.putProviders as Mock).mockResolvedValue({ success: true })
      ;(api.getStatus as Mock).mockResolvedValue({ running: true, pid: 123, uptime_seconds: 60, service_url: 'http://localhost:4000', version: '1.0.0' })
      ;(api.getModels as Mock).mockResolvedValue({ models: [], total: 0, available: 0, unavailable: 0 })
      ;(api.getProviders as Mock).mockResolvedValue({ providers: [] })

      await useDashboardStore.getState().saveProviders({ openai: { api_base: 'https://api.openai.com', timeout: 30 } })

      const state = useDashboardStore.getState()
      expect(state.toast).toEqual({ message: 'Provider 配置已保存', type: 'success' })
      expect(state.isSavingProviders).toBe(false)
      expect(state.error).toBeNull()
    })

    it('shows error toast when backend returns errors', async () => {
      ;(api.putProviders as Mock).mockResolvedValue({ success: false, errors: ['invalid base'] })

      await useDashboardStore.getState().saveProviders({ openai: { api_base: 'bad', timeout: 30 } })

      const state = useDashboardStore.getState()
      expect(state.error).toBe('invalid base')
      expect(state.toast).toEqual({ message: '保存失败', type: 'error' })
      expect(state.isSavingProviders).toBe(false)
    })

    it('shows error on exception', async () => {
      ;(api.putProviders as Mock).mockRejectedValue(new Error('timeout'))

      await useDashboardStore.getState().saveProviders({ openai: { api_base: 'https://api.openai.com', timeout: 30 } })

      const state = useDashboardStore.getState()
      expect(state.error).toBe('timeout')
      expect(state.toast).toEqual({ message: 'timeout', type: 'error' })
      expect(state.isSavingProviders).toBe(false)
    })
  })

  describe('setModelsFilter', () => {
    it('updates filter', () => {
      useDashboardStore.getState().setModelsFilter('gpt')
      expect(useDashboardStore.getState().modelsFilter).toBe('gpt')
    })
  })

  describe('setModelsSort', () => {
    it('toggles asc when same key', () => {
      useDashboardStore.getState().setModelsSort('name')
      expect(useDashboardStore.getState().modelsSort).toEqual({ key: 'name', asc: false })
    })

    it('sets asc true when different key', () => {
      useDashboardStore.setState({ modelsSort: { key: 'name', asc: false } })
      useDashboardStore.getState().setModelsSort('quality')
      expect(useDashboardStore.getState().modelsSort).toEqual({ key: 'quality', asc: true })
    })
  })

  describe('clearError', () => {
    it('clears error', () => {
      useDashboardStore.setState({ error: 'oops' })
      useDashboardStore.getState().clearError()
      expect(useDashboardStore.getState().error).toBeNull()
    })
  })

  describe('clearToast', () => {
    it('clears toast', () => {
      useDashboardStore.setState({ toast: { message: 'hi', type: 'success' } })
      useDashboardStore.getState().clearToast()
      expect(useDashboardStore.getState().toast).toBeNull()
    })
  })
})
