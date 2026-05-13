import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGet, mockPost, mockPut, mockResUse, mockReqUse } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
  mockResUse: vi.fn(),
  mockReqUse: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      interceptors: {
        request: { use: mockReqUse },
        response: { use: mockResUse },
      },
    })),
    interceptors: { response: { use: vi.fn() } },
  },
}))

import { api } from './client'

describe('api client', () => {
  beforeEach(() => {
    mockGet.mockClear()
    mockPost.mockClear()
    mockPut.mockClear()
  })

  it('registers response interceptor', () => {
    expect(mockResUse).toHaveBeenCalledTimes(1)
    expect(mockResUse).toHaveBeenCalledWith(expect.any(Function), expect.any(Function))
  })

  describe('getStatus', () => {
    it('returns service status from /api/status', async () => {
      const data = { running: true, pid: 123, uptime_seconds: 60, service_url: 'http://localhost:4000', version: '1.0.0' }
      mockGet.mockResolvedValue({ data })

      const result = await api.getStatus()

      expect(mockGet).toHaveBeenCalledWith('/api/status')
      expect(result).toEqual(data)
    })
  })

  describe('getModels', () => {
    it('returns models from /api/models', async () => {
      const data = { models: [{ name: 'gpt-4', provider: 'openai', available: true, quality: 9, cost: 3, context: 8192, supported_tasks: ['chat'] }], total: 1, available: 1, unavailable: 0 }
      mockGet.mockResolvedValue({ data })

      const result = await api.getModels()

      expect(mockGet).toHaveBeenCalledWith('/api/models')
      expect(result).toEqual(data)
    })
  })

  describe('getProviders', () => {
    it('returns providers from /api/providers', async () => {
      const data = { providers: [{ name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true }] }
      mockGet.mockResolvedValue({ data })

      const result = await api.getProviders()

      expect(mockGet).toHaveBeenCalledWith('/api/providers')
      expect(result).toEqual(data)
    })
  })

  describe('dryRun', () => {
    it('posts prompt and strategy to /api/dry-run', async () => {
      const payload = { prompt: 'hello', strategy: 'auto' }
      const data = { task_type: 'chat', task_confidence: 0.9, difficulty: 'easy', difficulty_confidence: 0.8, selected_model: 'gpt-4', strategy: 'auto', score: 8.5, reason: 'fast' }
      mockPost.mockResolvedValue({ data })

      const result = await api.dryRun(payload)

      expect(mockPost).toHaveBeenCalledWith('/api/dry-run', payload)
      expect(result).toEqual(data)
    })
  })

  describe('stopService', () => {
    it('posts to /api/stop', async () => {
      mockPost.mockResolvedValue({ data: { success: true } })

      const result = await api.stopService()

      expect(mockPost).toHaveBeenCalledWith('/api/stop')
      expect(result).toEqual({ success: true })
    })
  })

  describe('putProviders', () => {
    it('puts providers payload to /api/providers', async () => {
      const payload = { openai: { api_base: 'https://api.openai.com', timeout: 30 } }
      const data = { success: true }
      mockPut.mockResolvedValue({ data })

      const result = await api.putProviders(payload)

      expect(mockPut).toHaveBeenCalledWith('/api/providers', { providers: payload })
      expect(result).toEqual(data)
    })
  })

  describe('getModelOverrides', () => {
    it('returns model overrides from /api/model-overrides', async () => {
      const data = { overrides: { openai: ['gpt-4o', 'gpt-4o-mini'], anthropic: ['claude-3'] } }
      mockGet.mockResolvedValue({ data })

      const result = await api.getModelOverrides()

      expect(mockGet).toHaveBeenCalledWith('/api/model-overrides')
      expect(result).toEqual(data)
    })
  })

  describe('toggleModel', () => {
    it('puts enabled state to /api/models/{provider}/{model}', async () => {
      const data = { success: true, provider: 'openai', model: 'gpt-4o', enabled: false }
      mockPut.mockResolvedValue({ data })

      const result = await api.toggleModel('openai', 'gpt-4o', false)

      expect(mockPut).toHaveBeenCalledWith('/api/models/openai/gpt-4o', { enabled: false })
      expect(result).toEqual(data)
    })
  })
})
