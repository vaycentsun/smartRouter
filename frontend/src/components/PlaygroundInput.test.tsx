import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PlaygroundInput } from './PlaygroundInput'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('PlaygroundInput', () => {
  const onSubmit = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockStoreState.models = [
      { name: 'gpt-4o', provider: 'openai', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
      { name: 'claude-3', provider: 'anthropic', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
    ]
    mockStoreState.isLoadingPlayground = false
  })

  it('renders input and model selection', () => {
    render(<PlaygroundInput onSubmit={onSubmit} />)
    expect(screen.getByPlaceholderText('例如：帮我写一个快速排序算法')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
    expect(screen.getByText('claude-3')).toBeInTheDocument()
  })

  it('submits with selected model and prompt', () => {
    render(<PlaygroundInput onSubmit={onSubmit} />)
    fireEvent.click(screen.getByText('gpt-4o'))
    fireEvent.change(screen.getByPlaceholderText('例如：帮我写一个快速排序算法'), {
      target: { value: 'Hello' },
    })
    fireEvent.click(screen.getByText('提交'))
    expect(onSubmit).toHaveBeenCalledWith({ mode: 'single', prompt: 'Hello', models: ['gpt-4o'] })
  })

  it('disables submit when no model selected', () => {
    render(<PlaygroundInput onSubmit={onSubmit} />)
    fireEvent.change(screen.getByPlaceholderText('例如：帮我写一个快速排序算法'), {
      target: { value: 'Hello' },
    })
    expect(screen.getByText('提交')).toBeDisabled()
  })

  it('limits model selection to 3', () => {
    mockStoreState.models = [
      { name: 'm1', provider: 'openai', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
      { name: 'm2', provider: 'openai', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
      { name: 'm3', provider: 'openai', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
      { name: 'm4', provider: 'openai', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
    ]
    render(<PlaygroundInput onSubmit={onSubmit} />)
    fireEvent.click(screen.getByText('m1'))
    fireEvent.click(screen.getByText('m2'))
    fireEvent.click(screen.getByText('m3'))
    fireEvent.click(screen.getByText('m4'))
    fireEvent.change(screen.getByPlaceholderText('例如：帮我写一个快速排序算法'), {
      target: { value: 'test' },
    })
    fireEvent.click(screen.getByText('提交'))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ models: ['m1', 'm2', 'm3'] }))
  })

  it('switches to compare mode', () => {
    render(<PlaygroundInput onSubmit={onSubmit} />)
    fireEvent.click(screen.getByText('对比模式'))
    fireEvent.click(screen.getByText('gpt-4o'))
    fireEvent.click(screen.getByText('claude-3'))
    fireEvent.change(screen.getByPlaceholderText('例如：帮我写一个快速排序算法'), {
      target: { value: 'Compare' },
    })
    fireEvent.click(screen.getByText('提交'))
    expect(onSubmit).toHaveBeenCalledWith({ mode: 'compare', prompt: 'Compare', models: ['gpt-4o', 'claude-3'] })
  })
})
