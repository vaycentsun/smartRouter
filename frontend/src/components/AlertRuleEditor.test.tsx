import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AlertRuleEditor } from './AlertRuleEditor'
import type { AlertRule } from '../types'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('AlertRuleEditor', () => {
  beforeEach(() => {
    mockStoreState.createAlertRule = vi.fn().mockResolvedValue(undefined)
    mockStoreState.updateAlertRule = vi.fn().mockResolvedValue(undefined)
    mockStoreState.testAlertRule = vi.fn().mockResolvedValue({ triggered: false, triggers: [] })
  })

  it('renders create mode', () => {
    render(<AlertRuleEditor onClose={vi.fn()} />)
    expect(screen.getByText('新建告警规则')).toBeInTheDocument()
    expect(screen.getByLabelText('规则 ID')).toBeInTheDocument()
  })

  it('renders edit mode with pre-filled data', () => {
    const rule: AlertRule = {
      id: 'rule-1',
      name: 'Test Rule',
      enabled: true,
      condition: { metric: 'daily_requests', operator: '>', threshold: 100 },
      severity: 'warning',
      time_window: '1d',
      channels: [{ type: 'log' }],
      cooldown_minutes: 60,
    }
    render(<AlertRuleEditor rule={rule} onClose={vi.fn()} />)
    expect(screen.getByText('编辑告警规则')).toBeInTheDocument()
    expect((screen.getByLabelText('规则 ID') as HTMLInputElement).value).toBe('rule-1')
    expect((screen.getByLabelText('规则名称') as HTMLInputElement).value).toBe('Test Rule')
  })

  it('calls onClose when cancel clicked', () => {
    const onClose = vi.fn()
    render(<AlertRuleEditor onClose={onClose} />)
    fireEvent.click(screen.getByText('取消'))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls createAlertRule on submit', () => {
    render(<AlertRuleEditor onClose={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('规则 ID'), { target: { value: 'new-rule' } })
    fireEvent.change(screen.getByLabelText('规则名称'), { target: { value: 'New Rule' } })
    fireEvent.click(screen.getByText('创建'))
    expect(mockStoreState.createAlertRule).toHaveBeenCalled()
  })
})
