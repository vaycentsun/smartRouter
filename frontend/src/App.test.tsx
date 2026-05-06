import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import App from './App'

vi.mock('./store/useDashboardStore')

import { mockStoreState } from './store/__mocks__/useDashboardStore'

describe('App', () => {
  beforeEach(() => {
    // Reset URL so wouter starts at root (will redirect to /dashboard)
    window.history.pushState({}, '', '/')
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
    mockStoreState.modelOverrides = {}
    mockStoreState.modelOverride = { provider: null, model: null, enabled: false }
    mockStoreState.setModelOverride = vi.fn()
    mockStoreState.clearModelOverride = vi.fn()
    mockStoreState.logs = { lines: [], offset: 0, total_size: 0, source: 'service' }
    mockStoreState.isLoadingLogs = false
    mockStoreState.logError = null
    mockStoreState.fetchLogs = vi.fn().mockResolvedValue(undefined)
    mockStoreState.setLogSource = vi.fn()
    mockStoreState.clearLogError = vi.fn()
    mockStoreState.isCheckingHealth = {}
    mockStoreState.checkProviderHealth = vi.fn().mockResolvedValue(undefined)
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

  it('renders dashboard tab by default', () => {
    render(<App />)
    expect(screen.getByText('仪表盘')).toBeInTheDocument()
    expect(screen.getByText('模型清单')).toBeInTheDocument()
    expect(screen.getByText('模型总数')).toBeInTheDocument()
  })

  it('switches to models tab when clicked', () => {
    render(<App />)
    fireEvent.click(screen.getByText('模型清单'))
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()
  })

  it('stops periodic fetchAll when switching away from dashboard', () => {
    vi.useFakeTimers()
    render(<App />)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(1)

    // Switch to models tab
    fireEvent.click(screen.getByText('模型清单'))
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()

    // Advance time; fetchAll should NOT be called again
    vi.advanceTimersByTime(5000)
    expect(mockStoreState.fetchAll).toHaveBeenCalledTimes(1)

    vi.useRealTimers()
  })
})
