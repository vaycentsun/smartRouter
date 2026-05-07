import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TokenStatsPage } from './TokenStatsPage'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

const mockStats = [
  { model: 'gpt-4o', prompt_tokens: 1000, completion_tokens: 500, total_tokens: 1500, reasoning_tokens: 100, cached_tokens: 50, request_count: 10 },
]

describe('TokenStatsPage', () => {
  beforeEach(() => {
    mockStoreState.tokenStats = mockStats
  })

  it('renders overview cards', () => {
    render(<TokenStatsPage />)
    expect(screen.getByText('总请求数')).toBeInTheDocument()
    expect(screen.getByText('总输入 Token')).toBeInTheDocument()
    expect(screen.getByText('总输出 Token')).toBeInTheDocument()
    expect(screen.getAllByText('推理 Token')).toHaveLength(2)
    expect(screen.getAllByText('缓存命中')).toHaveLength(2)
  })

  it('renders table section', () => {
    render(<TokenStatsPage />)
    expect(screen.getByText('模型消耗明细')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o')).toBeInTheDocument()
  })

  it('renders chart section', () => {
    render(<TokenStatsPage />)
    expect(screen.getByText('Token 分布')).toBeInTheDocument()
  })

  it('shows zero values when no data', () => {
    mockStoreState.tokenStats = []
    render(<TokenStatsPage />)
    expect(screen.getAllByText('0')).toHaveLength(5)
  })
})
