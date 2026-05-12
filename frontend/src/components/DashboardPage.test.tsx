import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DashboardPage } from './DashboardPage'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('DashboardPage', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.status = { running: true, pid: 1234, uptime_seconds: 3600, service_url: 'http://localhost:4000', version: '1.0.0' }
    mockStoreState.models = []
    mockStoreState.providers = []
    mockStoreState.dryRunResult = null
    mockStoreState.isLoading = false
    mockStoreState.error = null
    mockStoreState.toast = null
    mockStoreState.isSavingProviders = false
    mockStoreState.modelsFilter = ''
    mockStoreState.modelsSort = { key: 'name', asc: true }
    mockStoreState.fetchAll = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearError = vi.fn()
    mockStoreState.runDryRun = vi.fn().mockResolvedValue(undefined)
    mockStoreState.stopService = vi.fn().mockResolvedValue(undefined)
    mockStoreState.saveProviders = vi.fn().mockResolvedValue(undefined)
    mockStoreState.setModelsFilter = vi.fn()
    mockStoreState.setModelsSort = vi.fn()
    mockStoreState.clearToast = vi.fn()
    mockStoreState.fetchErrorStats = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearErrorStatsError = vi.fn()
  })

  it('renders stats overview, status card and dry run panel', () => {
    render(<DashboardPage />)
    expect(screen.getByText('模型总数')).toBeInTheDocument()
    expect(screen.getByText('Provider 数')).toBeInTheDocument()
    expect(screen.getAllByText('服务状态').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('快速路由测试')).toBeInTheDocument()
  })
})
