import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatsOverview } from './StatsOverview'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('StatsOverview', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
  })

  it('renders model count and available sublabel', () => {
    mockStoreState.models = [
      { name: 'gpt-4', provider: 'openai', available: true, quality: 9, cost: 3, context: 8192, supported_tasks: ['chat'] },
      { name: 'gpt-3.5', provider: 'openai', available: false, quality: 7, cost: 1, context: 4096, supported_tasks: ['chat'] },
    ]
    mockStoreState.providers = []
    mockStoreState.status = null
    render(<StatsOverview />)
    expect(screen.getByText('模型总数')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('1 可用')).toBeInTheDocument()
  })

  it('renders provider count and missing keys sublabel', () => {
    mockStoreState.models = []
    mockStoreState.providers = [
      { name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true },
      { name: 'azure', api_base: 'https://azure.com', timeout: 30, key_type: 'env:AZURE_KEY', has_key: false },
    ]
    mockStoreState.status = null
    render(<StatsOverview />)
    expect(screen.getByText('Provider 数')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('1 Key 缺失')).toBeInTheDocument()
  })

  it('renders running status with pid sublabel', () => {
    mockStoreState.models = []
    mockStoreState.providers = []
    mockStoreState.status = { running: true, pid: 123, uptime_seconds: 60, service_url: 'http://localhost:4000', version: '1.0.0' }
    render(<StatsOverview />)
    expect(screen.getByText('服务状态')).toBeInTheDocument()
    expect(screen.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByText('PID: 123')).toBeInTheDocument()
  })

  it('renders stopped status with dash sublabel', () => {
    mockStoreState.models = []
    mockStoreState.providers = []
    mockStoreState.status = { running: false, pid: null, uptime_seconds: null, service_url: null, version: '1.0.0' }
    render(<StatsOverview />)
    expect(screen.getByText('已停止')).toBeInTheDocument()
    expect(screen.getByText('-')).toBeInTheDocument()
  })
})
