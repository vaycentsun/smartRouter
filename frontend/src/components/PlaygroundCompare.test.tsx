import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PlaygroundCompare } from './PlaygroundCompare'

describe('PlaygroundCompare', () => {
  const mockResults = [
    { model: 'gpt-4o', provider: 'openai', response: 'A', latency_ms: 100, prompt_tokens: 10, completion_tokens: 5, estimated_cost: 0.001, error: null, routing_info: null },
    { model: 'claude-3', provider: 'anthropic', response: 'B', latency_ms: 200, prompt_tokens: 10, completion_tokens: 5, estimated_cost: 0.002, error: null, routing_info: null },
  ]

  it('renders multiple model cards', () => {
    render(<PlaygroundCompare results={mockResults} />)
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
    expect(screen.getByText('claude-3')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('renders error state', () => {
    const errorResults = [
      { ...mockResults[0], error: 'Timeout', response: '' },
    ]
    render(<PlaygroundCompare results={errorResults} />)
    expect(screen.getByText('Timeout')).toBeInTheDocument()
  })

  it('renders meta info', () => {
    render(<PlaygroundCompare results={mockResults} />)
    expect(screen.getByText('100ms')).toBeInTheDocument()
    expect(screen.getByText('200ms')).toBeInTheDocument()
  })
})
