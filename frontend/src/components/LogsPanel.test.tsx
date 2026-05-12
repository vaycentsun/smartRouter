import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LogsPanel } from './LogsPanel'
import * as storeModule from '../store/useDashboardStore'

vi.mock('../store/useDashboardStore')

const createMockStore = (overrides = {}) => ({
  logs: { lines: [], offset: 0, total_size: 0, source: 'service' as const },
  fetchLogs: vi.fn(),
  setLogSource: vi.fn(),
  setLogLevel: vi.fn(),
  logError: null,
  clearLogError: vi.fn(),
  ...overrides,
})

describe('LogsPanel', () => {
  it('renders empty state', () => {
    vi.mocked(storeModule.useDashboardStore).mockReturnValue(createMockStore())
    render(<LogsPanel />)
    expect(screen.getByText('暂无日志')).toBeInTheDocument()
  })

  it('renders log lines', () => {
    vi.mocked(storeModule.useDashboardStore).mockReturnValue(
      createMockStore({
        logs: {
          lines: ['INFO: started', 'ERROR: failed'],
          offset: 100,
          total_size: 100,
          source: 'service' as const,
        },
      })
    )
    render(<LogsPanel />)
    expect(screen.getByText('INFO: started')).toBeInTheDocument()
    expect(screen.getByText('ERROR: failed')).toBeInTheDocument()
  })

  it('switches log source on tab click', () => {
    const setLogSource = vi.fn()
    vi.mocked(storeModule.useDashboardStore).mockReturnValue(
      createMockStore({ setLogSource })
    )
    render(<LogsPanel />)
    fireEvent.click(screen.getByText('Dashboard 日志'))
    expect(setLogSource).toHaveBeenCalledWith('dashboard')
  })
})
