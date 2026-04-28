import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModelsTable } from './ModelsTable'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('ModelsTable', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.modelsFilter = ''
    mockStoreState.modelsSort = { key: 'name', asc: true }
    mockStoreState.setModelsFilter = vi.fn()
    mockStoreState.setModelsSort = vi.fn()
  })

  const sampleModels = [
    { name: 'gpt-4', provider: 'openai', available: true, quality: 9, cost: 3, context: 8192, supported_tasks: ['chat', 'code'] },
    { name: 'claude-3', provider: 'anthropic', available: false, quality: 8, cost: 4, context: 200000, supported_tasks: ['chat', 'analysis', 'writing', 'code'] },
    { name: 'gpt-3.5', provider: 'openai', available: true, quality: 7, cost: 1, context: 4096, supported_tasks: ['chat'] },
  ]

  it('renders empty state when no models', () => {
    mockStoreState.models = []
    render(<ModelsTable />)
    expect(screen.getByText('暂无模型数据，请检查配置')).toBeInTheDocument()
  })

  it('filters by model name', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsFilter = 'gpt'
    render(<ModelsTable />)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('gpt-3.5')).toBeInTheDocument()
    expect(screen.queryByText('claude-3')).not.toBeInTheDocument()
  })

  it('filters by provider name', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsFilter = 'anthropic'
    render(<ModelsTable />)
    expect(screen.getByText('claude-3')).toBeInTheDocument()
    expect(screen.queryByText('gpt-4')).not.toBeInTheDocument()
  })

  it('shows no match message when filter returns nothing', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsFilter = 'xyz'
    render(<ModelsTable />)
    expect(screen.getByText('没有匹配的模型')).toBeInTheDocument()
  })

  it('sorts by string column ascending', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsSort = { key: 'name', asc: true }
    render(<ModelsTable />)
    const rows = screen.getAllByRole('row')
    // Skip header row
    expect(rows[1]).toHaveTextContent('claude-3')
    expect(rows[2]).toHaveTextContent('gpt-3.5')
    expect(rows[3]).toHaveTextContent('gpt-4')
  })

  it('sorts by string column descending', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsSort = { key: 'name', asc: false }
    render(<ModelsTable />)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('gpt-4')
    expect(rows[2]).toHaveTextContent('gpt-3.5')
    expect(rows[3]).toHaveTextContent('claude-3')
  })

  it('sorts by number column', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsSort = { key: 'quality', asc: true }
    render(<ModelsTable />)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('gpt-3.5') // quality 7
    expect(rows[2]).toHaveTextContent('claude-3') // quality 8
    expect(rows[3]).toHaveTextContent('gpt-4') // quality 9
  })

  it('sorts by boolean column', () => {
    mockStoreState.models = sampleModels
    mockStoreState.modelsSort = { key: 'available', asc: true }
    render(<ModelsTable />)
    const rows = screen.getAllByRole('row')
    // true comes before false when asc (aVal ? -1 : 1)
    expect(rows[1]).toHaveTextContent('gpt-4') // true
    expect(rows[2]).toHaveTextContent('gpt-3.5') // true
    expect(rows[3]).toHaveTextContent('claude-3') // false
  })

  it('formats large context as k', () => {
    mockStoreState.models = sampleModels
    render(<ModelsTable />)
    expect(screen.getByText('200k')).toBeInTheDocument()
    expect(screen.getByText('8k')).toBeInTheDocument()
    expect(screen.getByText('4k')).toBeInTheDocument() // 4096 -> 4k
  })

  it('shows task badges and overflow count', () => {
    mockStoreState.models = sampleModels
    render(<ModelsTable />)
    expect(screen.getByText('analysis')).toBeInTheDocument()
    expect(screen.getByText('writing')).toBeInTheDocument()
    expect(screen.getByText('+1')).toBeInTheDocument() // claude-3 has 4 tasks, shows 3 + +1
  })

  it('calls setModelsSort when header clicked', () => {
    mockStoreState.models = sampleModels
    render(<ModelsTable />)
    fireEvent.click(screen.getByText('模型名称'))
    expect(mockStoreState.setModelsSort).toHaveBeenCalledWith('name')
  })

  it('calls setModelsFilter on input change', () => {
    mockStoreState.models = sampleModels
    render(<ModelsTable />)
    const input = screen.getByPlaceholderText('搜索模型或 Provider...')
    fireEvent.change(input, { target: { value: 'gpt' } })
    expect(mockStoreState.setModelsFilter).toHaveBeenCalledWith('gpt')
  })
})
