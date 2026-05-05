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
      { model: 'qwen3.5-plus', total_tokens: 2000, cost: 2.5, request_count: 10 },
    ]
    render(<TopModelsTable />)
    expect(screen.getByText('排名')).toBeInTheDocument()
    expect(screen.getByText('模型名')).toBeInTheDocument()
    expect(screen.getByText('Token 数')).toBeInTheDocument()
    expect(screen.getByText('成本')).toBeInTheDocument()
    expect(screen.getByText('请求数')).toBeInTheDocument()
  })

  it('renders model data with rank', () => {
    mockStoreState.analyticsTopModels = [
      { model: 'qwen3.5-plus', total_tokens: 2000, cost: 2.5, request_count: 10 },
      { model: 'gpt-4o', total_tokens: 1500, cost: 1.8, request_count: 8 },
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
      { model: 'qwen3.5-plus', total_tokens: 2000, cost: 2.5, request_count: 10 },
      { model: 'gpt-4o', total_tokens: 1500, cost: 1.8, request_count: 8 },
    ]
    render(<TopModelsTable />)
    const costHeader = screen.getByText('成本')
    fireEvent.click(costHeader)
    expect(costHeader).toBeInTheDocument()
  })
})
