import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CostTrendChart } from './CostTrendChart'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('CostTrendChart', () => {
  beforeEach(() => {
    mockStoreState.analyticsDaily = []
  })

  it('renders chart title', () => {
    mockStoreState.analyticsDaily = [
      { date: '2026-05-01', cost: 2.5, requests: 6, tokens: 1800 },
    ]
    render(<CostTrendChart />)
    expect(screen.getByText('成本趋势')).toBeInTheDocument()
  })

  it('shows empty state when no data', () => {
    mockStoreState.analyticsDaily = []
    render(<CostTrendChart />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })
})
