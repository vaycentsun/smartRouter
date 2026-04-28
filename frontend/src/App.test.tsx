import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import App from './App'

vi.mock('./store/useDashboardStore')

import { mockStoreState } from './store/__mocks__/useDashboardStore'

describe('App', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.fetchAll = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearError = vi.fn()
    mockStoreState.error = null
    mockStoreState.models = []
    mockStoreState.providers = []
    mockStoreState.status = null
    mockStoreState.modelsFilter = ''
    mockStoreState.modelsSort = { key: 'name', asc: true }
    mockStoreState.isLoading = false
    mockStoreState.dryRunResult = null
    mockStoreState.toast = null
    mockStoreState.isSavingProviders = false
    mockStoreState.saveProviders = vi.fn().mockResolvedValue(undefined)
    mockStoreState.runDryRun = vi.fn().mockResolvedValue(undefined)
    mockStoreState.stopService = vi.fn().mockResolvedValue(undefined)
    mockStoreState.setModelsFilter = vi.fn()
    mockStoreState.setModelsSort = vi.fn()
    mockStoreState.clearToast = vi.fn()
  })

  it('calls fetchAll on mount', () => {
    render(<App />)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(1)
  })

  it('calls fetchAll periodically', () => {
    vi.useFakeTimers()
    render(<App />)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(5000)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(2)
    vi.advanceTimersByTime(5000)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(3)
    vi.useRealTimers()
  })

  it('cleans up interval on unmount', () => {
    vi.useFakeTimers()
    const { unmount } = render(<App />)
    unmount()
    vi.advanceTimersByTime(5000)
    // fetchAll should still only be called once (on mount)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('shows error alert when error exists', () => {
    mockStoreState.error = 'Connection failed'
    render(<App />)
    expect(screen.getAllByText('Connection failed').length).toBeGreaterThanOrEqual(1)
  })

  it('calls clearError when error close button clicked', () => {
    mockStoreState.error = 'Connection failed'
    render(<App />)
    fireEvent.click(screen.getAllByText('关闭')[0])
    expect(mockStoreState.clearError).toHaveBeenCalled()
  })

  it('renders main sections', () => {
    mockStoreState.models = []
    mockStoreState.providers = []
    mockStoreState.status = null
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Smart Router Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('服务状态')).toBeInTheDocument()
    expect(screen.getByText('快速路由测试')).toBeInTheDocument()
    expect(screen.getByText('Provider 配置')).toBeInTheDocument()
    expect(screen.getByText('模型列表')).toBeInTheDocument()
  })
})
