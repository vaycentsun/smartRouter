import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SummaryCards } from './SummaryCards'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('SummaryCards', () => {
  beforeEach(() => {
    mockStoreState.analyticsSummary = null
    mockStoreState.isLoadingAnalytics = false
  })

  it('renders four stat cards with labels', () => {
    mockStoreState.analyticsSummary = {
      total_cost: 15.3,
      total_requests: 42,
      total_tokens: 12500,
      avg_daily_cost: 2.18,
      incomplete: false,
    }
    render(<SummaryCards />)
    expect(screen.getByText('总成本')).toBeInTheDocument()
    expect(screen.getByText('总请求数')).toBeInTheDocument()
    expect(screen.getByText('总 Token 数')).toBeInTheDocument()
    expect(screen.getByText('日均成本')).toBeInTheDocument()
  })

  it('displays formatted values', () => {
    mockStoreState.analyticsSummary = {
      total_cost: 15.3,
      total_requests: 42,
      total_tokens: 12500,
      avg_daily_cost: 2.18,
      incomplete: false,
    }
    render(<SummaryCards />)
    expect(screen.getByText('¥15.30')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('12,500')).toBeInTheDocument()
    expect(screen.getByText('¥2.18')).toBeInTheDocument()
  })

  it('shows asterisk when incomplete is true', () => {
    mockStoreState.analyticsSummary = {
      total_cost: 15.3,
      total_requests: 42,
      total_tokens: 12500,
      avg_daily_cost: 2.18,
      incomplete: true,
    }
    render(<SummaryCards />)
    expect(screen.getAllByText('*')).toHaveLength(2)
  })

  it('shows placeholder when data is null', () => {
    mockStoreState.analyticsSummary = null
    render(<SummaryCards />)
    const placeholders = screen.getAllByText('--')
    expect(placeholders.length).toBeGreaterThanOrEqual(4)
  })

  it('shows placeholder for null cost values', () => {
    mockStoreState.analyticsSummary = {
      total_cost: null,
      total_requests: 10,
      total_tokens: 1000,
      avg_daily_cost: null,
      incomplete: true,
    }
    render(<SummaryCards />)
    const placeholders = screen.getAllByText('--')
    expect(placeholders.length).toBeGreaterThanOrEqual(2)
  })
})
