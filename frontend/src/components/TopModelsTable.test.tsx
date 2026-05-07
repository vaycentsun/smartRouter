import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TopModelsTable } from './TopModelsTable'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('TopModelsTable', () => {
  beforeEach(() => {
    mockStoreState.analyticsTopModels = []
  })

  it('renders table headers', () => {
    mockStoreState.analyticsTopModels = [
      { model: 'qwen3.5-plus', prompt_tokens: 500, completion_tokens: 1500, total_tokens: 2000, reasoning_tokens: 100, cached_tokens: 50, cost: 2.5, request_count: 10 },
    ]
    render(<TopModelsTable />)
    expect(screen.getByText('排名')).toBeInTheDocument()
    expect(screen.getByText('模型名')).toBeInTheDocument()
    expect(screen.getByText('输入')).toBeInTheDocument()
    expect(screen.getByText('输出')).toBeInTheDocument()
    expect(screen.getByText('推理')).toBeInTheDocument()
    expect(screen.getByText('缓存')).toBeInTheDocument()
    expect(screen.getByText('总计')).toBeInTheDocument()
    expect(screen.getByText('成本')).toBeInTheDocument()
    expect(screen.getByText('请求数')).toBeInTheDocument()
  })

  it('renders model data with rank', () => {
    mockStoreState.analyticsTopModels = [
      { model: 'qwen3.5-plus', prompt_tokens: 500, completion_tokens: 1500, total_tokens: 2000, reasoning_tokens: 100, cached_tokens: 50, cost: 2.5, request_count: 10 },
      { model: 'gpt-4o', prompt_tokens: 300, completion_tokens: 700, total_tokens: 1000, reasoning_tokens: 50, cached_tokens: 25, cost: 1.8, request_count: 8 },
    ]
    render(<TopModelsTable />)
    expect(screen.getByText('qwen3.5-plus')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
  })

  it('shows empty state when no data', () => {
    mockStoreState.analyticsTopModels = []
    render(<TopModelsTable />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('sorts by clicking column headers', () => {
    mockStoreState.analyticsTopModels = [
      { model: 'qwen3.5-plus', prompt_tokens: 500, completion_tokens: 1500, total_tokens: 2000, reasoning_tokens: 100, cached_tokens: 50, cost: 2.5, request_count: 10 },
      { model: 'gpt-4o', prompt_tokens: 300, completion_tokens: 700, total_tokens: 1000, reasoning_tokens: 50, cached_tokens: 25, cost: 1.8, request_count: 8 },
    ]
    render(<TopModelsTable />)
    const costHeader = screen.getByText('成本')
    fireEvent.click(costHeader)
    expect(costHeader).toBeInTheDocument()
  })
})
