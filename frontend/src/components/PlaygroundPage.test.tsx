import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PlaygroundPage } from './PlaygroundPage'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('PlaygroundPage', () => {
  beforeEach(() => {
    mockStoreState.models = [
      { name: 'gpt-4o', provider: 'openai', available: true, quality: 9, cost: 3, context: 128000, supported_tasks: ['chat'] },
    ]
    mockStoreState.playgroundResults = []
    mockStoreState.playgroundError = null
    mockStoreState.isLoadingPlayground = false
    mockStoreState.fetchPlaygroundHistory = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearPlaygroundError = vi.fn()
    mockStoreState.runPlayground = vi.fn().mockResolvedValue(undefined)
  })

  it('renders input section', () => {
    render(<PlaygroundPage />)
    expect(screen.getByText('Playground')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('例如：帮我写一个快速排序算法')).toBeInTheDocument()
  })

  it('shows error state', () => {
    mockStoreState.playgroundError = 'Network error'
    render(<PlaygroundPage />)
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('shows single result', () => {
    mockStoreState.playgroundResults = [
      { model: 'gpt-4o', provider: 'openai', response: 'Hello', latency_ms: 100, prompt_tokens: 10, completion_tokens: 5, estimated_cost: 0.001, error: null, routing_info: null },
    ]
    render(<PlaygroundPage />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('shows compare results', () => {
    mockStoreState.playgroundResults = [
      { model: 'gpt-4o', provider: 'openai', response: 'A', latency_ms: 100, prompt_tokens: 10, completion_tokens: 5, estimated_cost: 0.001, error: null, routing_info: null },
      { model: 'claude-3', provider: 'anthropic', response: 'B', latency_ms: 200, prompt_tokens: 10, completion_tokens: 5, estimated_cost: 0.002, error: null, routing_info: null },
    ]
    render(<PlaygroundPage />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('calls fetchPlaygroundHistory on mount', () => {
    const fetchPlaygroundHistory = vi.fn().mockResolvedValue(undefined)
    mockStoreState.fetchPlaygroundHistory = fetchPlaygroundHistory
    render(<PlaygroundPage />)
    expect(fetchPlaygroundHistory).toHaveBeenCalled()
  })
})
