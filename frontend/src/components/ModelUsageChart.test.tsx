import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModelUsageChart } from './ModelUsageChart'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('ModelUsageChart', () => {
  beforeEach(() => {
    mockStoreState.analyticsByModel = []
  })

  it('renders chart title', () => {
    mockStoreState.analyticsByModel = [
      { model: 'qwen3.5-plus', prompt_tokens: 500, completion_tokens: 1500, cost: 2.5, request_count: 10 },
    ]
    render(<ModelUsageChart />)
    expect(screen.getByText('模型使用分布')).toBeInTheDocument()
  })

  it('shows empty state when no data', () => {
    mockStoreState.analyticsByModel = []
    render(<ModelUsageChart />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('toggles between pie and bar chart', () => {
    mockStoreState.analyticsByModel = [
      { model: 'qwen3.5-plus', prompt_tokens: 500, completion_tokens: 1500, cost: 2.5, request_count: 10 },
      { model: 'gpt-4o', prompt_tokens: 300, completion_tokens: 700, cost: 1.5, request_count: 5 },
    ]
    render(<ModelUsageChart />)
    expect(screen.getByText('饼图')).toBeInTheDocument()
    expect(screen.getByText('柱状图')).toBeInTheDocument()
    const barBtn = screen.getByText('柱状图')
    fireEvent.click(barBtn)
    expect(barBtn).toHaveClass('bg-[rgba(0,122,255,0.1)]')
  })
})
