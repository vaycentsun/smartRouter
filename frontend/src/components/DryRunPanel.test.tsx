import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DryRunPanel } from './DryRunPanel'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('DryRunPanel', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.runDryRun = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearError = vi.fn()
    mockStoreState.isLoading = false
    mockStoreState.error = null
    mockStoreState.dryRunResult = null
  })

  it('does not call runDryRun when prompt is empty', async () => {
    render(<DryRunPanel />)
    const button = screen.getByText('测试路由')
    fireEvent.click(button)
    expect(mockStoreState.runDryRun).not.toHaveBeenCalled()
  })

  it('calls runDryRun with prompt and strategy on submit', async () => {
    render(<DryRunPanel />)
    const textarea = screen.getByPlaceholderText('例如：帮我写一个快速排序算法')
    fireEvent.change(textarea, { target: { value: 'hello world' } })

    const button = screen.getByText('测试路由')
    fireEvent.click(button)

    expect(mockStoreState.clearError).toHaveBeenCalled()
    expect(mockStoreState.runDryRun).toHaveBeenCalledWith('hello world', 'auto')
  })

  it('switches strategy when button clicked', () => {
    render(<DryRunPanel />)
    fireEvent.click(screen.getByText('Quality'))
    const textarea = screen.getByPlaceholderText('例如：帮我写一个快速排序算法')
    fireEvent.change(textarea, { target: { value: 'test' } })
    fireEvent.click(screen.getByText('测试路由'))
    expect(mockStoreState.runDryRun).toHaveBeenCalledWith('test', 'quality')
  })

  it('shows loading state', () => {
    mockStoreState.isLoading = true
    render(<DryRunPanel />)
    expect(screen.getByText('测试中...')).toBeInTheDocument()
  })

  it('shows error message', () => {
    mockStoreState.error = 'Something went wrong'
    render(<DryRunPanel />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('shows dry run result', () => {
    mockStoreState.dryRunResult = {
      task_type: 'chat',
      task_confidence: 0.95,
      difficulty: 'easy',
      difficulty_confidence: 0.9,
      selected_model: 'gpt-4',
      strategy: 'quality',
      score: 9.2,
      reason: 'Highest quality match',
    }
    render(<DryRunPanel />)
    expect(screen.getByText('chat')).toBeInTheDocument()
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('Highest quality match')).toBeInTheDocument()
    expect(screen.getByText('9.2')).toBeInTheDocument()
  })

  it('does not show result when error field is present', () => {
    mockStoreState.dryRunResult = {
      task_type: 'chat',
      task_confidence: 0.5,
      difficulty: 'easy',
      difficulty_confidence: 0.5,
      selected_model: '',
      strategy: 'auto',
      score: 0,
      reason: '',
      error: 'No model available',
    }
    render(<DryRunPanel />)
    expect(screen.queryByText('路由结果')).not.toBeInTheDocument()
  })
})
