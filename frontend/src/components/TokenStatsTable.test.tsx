import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TokenStatsTable } from './TokenStatsTable'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

const mockTokenStats = [
  { model: 'gpt-4o', prompt_tokens: 1000, completion_tokens: 500, total_tokens: 1500, request_count: 10 },
  { model: 'claude-3', prompt_tokens: 2000, completion_tokens: 1000, total_tokens: 3000, request_count: 5 },
]

describe('TokenStatsTable', () => {
  beforeEach(() => {
    mockStoreState.tokenStats = mockTokenStats
  })

  it('renders table with data', () => {
    render(<TokenStatsTable />)
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
    expect(screen.getByText('claude-3')).toBeInTheDocument()
  })

  it('sorts by total_tokens descending by default', () => {
    render(<TokenStatsTable />)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('claude-3')
    expect(rows[2]).toHaveTextContent('gpt-4o')
  })

  it('toggles sort order when clicking same column', () => {
    render(<TokenStatsTable />)
    const totalHeader = screen.getByText('总计 Token')
    fireEvent.click(totalHeader)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('gpt-4o')
    expect(rows[2]).toHaveTextContent('claude-3')
  })

  it('changes sort column when clicking different column', () => {
    render(<TokenStatsTable />)
    const requestHeader = screen.getByText('请求次数')
    fireEvent.click(requestHeader)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('gpt-4o')
  })

  it('shows empty state when no data', () => {
    mockStoreState.tokenStats = []
    render(<TokenStatsTable />)
    expect(screen.getByText('暂无数据，发送请求后将自动统计')).toBeInTheDocument()
  })
})
