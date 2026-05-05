import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AlertRulesTable } from './AlertRulesTable'
import type { AlertRule } from '../types'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('AlertRulesTable', () => {
  beforeEach(() => {
    mockStoreState.alertRules = []
    mockStoreState.isLoadingAlerts = false
    mockStoreState.updateAlertRule = vi.fn().mockResolvedValue(undefined)
    mockStoreState.deleteAlertRule = vi.fn().mockResolvedValue(undefined)
  })

  it('renders empty state', () => {
    render(<AlertRulesTable onEdit={vi.fn()} />)
    expect(screen.getByText('暂无告警规则')).toBeInTheDocument()
  })

  it('renders rules with correct data', () => {
    mockStoreState.alertRules = [
      {
        id: 'rule-1',
        name: '高请求数',
        enabled: true,
        condition: { metric: 'daily_requests', operator: '>', threshold: 100 },
        severity: 'warning',
        time_window: '1d',
        channels: [{ type: 'log' }],
        cooldown_minutes: 60,
      },
    ]
    render(<AlertRulesTable onEdit={vi.fn()} />)
    expect(screen.getByText('高请求数')).toBeInTheDocument()
    expect(screen.getByText('daily_requests')).toBeInTheDocument()
    expect(screen.getByText('> 100')).toBeInTheDocument()
    expect(screen.getByText('warning')).toBeInTheDocument()
  })

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn()
    const rules: AlertRule[] = [
      {
        id: 'rule-1',
        name: 'Test',
        enabled: true,
        condition: { metric: 'daily_requests', operator: '>', threshold: 100 },
        severity: 'warning',
        time_window: '1d',
        channels: [],
        cooldown_minutes: 60,
      },
    ]
    mockStoreState.alertRules = rules
    render(<AlertRulesTable onEdit={onEdit} />)
    fireEvent.click(screen.getByText('编辑'))
    expect(onEdit).toHaveBeenCalledWith(rules[0])
  })

  it('toggles rule enabled state', () => {
    mockStoreState.alertRules = [
      {
        id: 'rule-1',
        name: 'Test',
        enabled: true,
        condition: { metric: 'daily_requests', operator: '>', threshold: 100 },
        severity: 'warning',
        time_window: '1d',
        channels: [],
        cooldown_minutes: 60,
      },
    ]
    render(<AlertRulesTable onEdit={vi.fn()} />)
    fireEvent.click(document.querySelector('button[class*="rounded-full"]')!)
    expect(mockStoreState.updateAlertRule).toHaveBeenCalledWith('rule-1', { enabled: false })
  })
})
