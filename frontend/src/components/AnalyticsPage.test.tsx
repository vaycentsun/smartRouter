import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AnalyticsPage } from './AnalyticsPage'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('AnalyticsPage', () => {
  beforeEach(() => {
    mockStoreState.analyticsSummary = null
    mockStoreState.analyticsDaily = []
    mockStoreState.analyticsByModel = []
    mockStoreState.analyticsTopModels = []
    mockStoreState.isLoadingAnalytics = false
    mockStoreState.analyticsError = null
  })

  it('renders all sections', () => {
    mockStoreState.analyticsSummary = {
      total_cost: 15.3,
      total_requests: 42,
      total_tokens: 12500,
      avg_daily_cost: 2.18,
      incomplete: false,
    }
    mockStoreState.analyticsDaily = [
      { date: '2026-05-01', cost: 2.5, requests: 6, tokens: 1800 },
    ]
    mockStoreState.analyticsByModel = [
      { model: 'qwen3.5-plus', prompt_tokens: 500, completion_tokens: 1500, cost: 2.5, request_count: 10 },
    ]
    mockStoreState.analyticsTopModels = [
      { model: 'qwen3.5-plus', total_tokens: 2000, cost: 2.5, request_count: 10 },
    ]
    render(<AnalyticsPage />)
    expect(screen.getByText('总成本')).toBeInTheDocument()
    expect(screen.getByText('成本趋势')).toBeInTheDocument()
    expect(screen.getByText('请求趋势')).toBeInTheDocument()
    expect(screen.getByText('模型使用分布')).toBeInTheDocument()
    expect(screen.getByText('热门模型排行')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    mockStoreState.isLoadingAnalytics = true
    render(<AnalyticsPage />)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('shows error state', () => {
    mockStoreState.analyticsError = 'Network error'
    render(<AnalyticsPage />)
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('calls fetchAnalytics on mount', () => {
    const fetchAnalytics = vi.fn()
    mockStoreState.fetchAnalytics = fetchAnalytics
    render(<AnalyticsPage />)
    expect(fetchAnalytics).toHaveBeenCalledWith(7)
  })
})
