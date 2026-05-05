import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AlertsPage } from './AlertsPage'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('AlertsPage', () => {
  beforeEach(() => {
    mockStoreState.alertRules = []
    mockStoreState.alertHistory = []
    mockStoreState.isLoadingAlerts = false
    mockStoreState.alertsError = null
    mockStoreState.fetchAlertRules = vi.fn().mockResolvedValue(undefined)
    mockStoreState.fetchAlertHistory = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearAlertsError = vi.fn()
  })

  it('renders alert page sections', () => {
    render(<AlertsPage />)
    expect(screen.getByText('活跃规则')).toBeInTheDocument()
    expect(screen.getByText('今日触发')).toBeInTheDocument()
    expect(screen.getByText('告警规则')).toBeInTheDocument()
    expect(screen.getByText('告警历史')).toBeInTheDocument()
  })

  it('shows error state', () => {
    mockStoreState.alertsError = 'Failed to load'
    render(<AlertsPage />)
    expect(screen.getByText('Failed to load')).toBeInTheDocument()
  })

  it('calls fetch on mount', () => {
    render(<AlertsPage />)
    expect(mockStoreState.fetchAlertRules).toHaveBeenCalled()
    expect(mockStoreState.fetchAlertHistory).toHaveBeenCalled()
  })

  it('shows new rule button', () => {
    render(<AlertsPage />)
    expect(screen.getByText('+ 新建规则')).toBeInTheDocument()
  })
})
