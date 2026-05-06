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
    fireEvent.click(screen.getByText('Cost'))
    const textarea = screen.getByPlaceholderText('例如：帮我写一个快速排序算法')
    fireEvent.change(textarea, { target: { value: 'test' } })
    fireEvent.click(screen.getByText('测试路由'))
    expect(mockStoreState.runDryRun).toHaveBeenCalledWith('test', 'cost')
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
      strategy: 'cost',
      score: 9.2,
      reason: 'Cheapest model with acceptable quality',
    }
    render(<DryRunPanel />)
    expect(screen.getByText('chat')).toBeInTheDocument()
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('Cheapest model with acceptable quality')).toBeInTheDocument()
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

  it('shows fallback chain when available', () => {
    mockStoreState.dryRunResult = {
      task_type: 'chat',
      task_confidence: 0.95,
      difficulty: 'easy',
      difficulty_confidence: 0.9,
      selected_model: 'gpt-4o',
      strategy: 'cost',
      score: 9.2,
      reason: 'Highest cost (cheapest)',
      fallback_chain: ['claude-3-opus', 'qwen-max'],
    }
    const { container } = render(<DryRunPanel />)
    expect(screen.getByText('Fallback 链')).toBeInTheDocument()
    // fallback 链文本可能被 span 分割，用 container 文本内容验证
    expect(container.textContent).toContain('gpt-4o')
    expect(container.textContent).toContain('claude-3-opus')
    expect(container.textContent).toContain('qwen-max')
  })

  it('does not show fallback chain when empty', () => {
    mockStoreState.dryRunResult = {
      task_type: 'chat',
      task_confidence: 0.95,
      difficulty: 'easy',
      difficulty_confidence: 0.9,
      selected_model: 'gpt-4o',
      strategy: 'cost',
      score: 9.2,
      reason: 'Highest cost (cheapest)',
      fallback_chain: [],
    }
    render(<DryRunPanel />)
    expect(screen.queryByText('Fallback 链')).not.toBeInTheDocument()
  })
})
