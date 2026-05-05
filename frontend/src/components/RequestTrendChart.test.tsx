import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RequestTrendChart } from './RequestTrendChart'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('RequestTrendChart', () => {
  beforeEach(() => {
    mockStoreState.analyticsDaily = []
  })

  it('renders chart title', () => {
    mockStoreState.analyticsDaily = [
      { date: '2026-05-01', cost: 2.5, requests: 6, tokens: 1800 },
    ]
    render(<RequestTrendChart />)
    expect(screen.getByText('请求趋势')).toBeInTheDocument()
  })

  it('shows empty state when no data', () => {
    mockStoreState.analyticsDaily = []
    render(<RequestTrendChart />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })
})
