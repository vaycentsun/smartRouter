import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RecentRequestsPanel } from './RecentRequestsPanel'
import type { RequestRoutingRecord } from '../types'

function formatTimeForTest(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('zh-CN', { hour12: false })
}

const mockRequests: RequestRoutingRecord[] = [
  {
    request_id: 'req-001',
    timestamp: '2024-01-15T14:32:05Z',
    original_model: 'gpt-4',
    selected_model: 'gpt-4o',
    actual_model: 'gpt-4o',
    task_type: 'chat',
    difficulty: 'medium',
    strategy: 'cost-optimized',
    fallback_chain: ['gpt-4o'],
    attempted_fallbacks: 0,
    did_fallback: false,
    status_code: 200,
    prompt_tokens: 150,
    completion_tokens: 80,
    total_tokens: 230,
    reasoning_tokens: 30,
    cached_tokens: 20,
    error_info: null,
  },
  {
    request_id: 'req-002',
    timestamp: '2024-01-15T14:33:10Z',
    original_model: 'claude-3-opus',
    selected_model: 'claude-3-sonnet',
    actual_model: 'claude-3-haiku',
    task_type: 'code',
    difficulty: 'hard',
    strategy: 'speed-priority',
    fallback_chain: ['claude-3-sonnet', 'claude-3-haiku'],
    attempted_fallbacks: 1,
    did_fallback: true,
    status_code: 200,
    prompt_tokens: 500,
    completion_tokens: 300,
    total_tokens: 800,
    reasoning_tokens: 60,
    cached_tokens: 40,
    error_info: null,
  },
  {
    request_id: 'req-003',
    timestamp: '2024-01-15T14:34:00Z',
    original_model: 'auto',
    selected_model: 'gpt-4o',
    actual_model: 'gpt-4o-mini',
    task_type: 'chat',
    difficulty: 'easy',
    strategy: 'auto',
    fallback_chain: ['gpt-4o', 'gpt-4o-mini'],
    attempted_fallbacks: 0,
    did_fallback: false,
    status_code: 200,
    prompt_tokens: 100,
    completion_tokens: 50,
    total_tokens: 150,
    error_info: null,
    retry_history: [
      { model: 'gpt-4o', status_code: 502, error: null, timestamp: '2024-01-15T14:34:00Z' },
      { model: 'gpt-4o-mini', status_code: 0, error: 'TimeoutError', timestamp: '2024-01-15T14:34:10Z' },
    ],
  },
]

describe('RecentRequestsPanel', () => {
  it('renders panel title', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    expect(screen.getByText('最近请求路由记录')).toBeInTheDocument()
  })

  it('shows empty state when no requests', () => {
    render(<RecentRequestsPanel requests={[]} />)
    expect(screen.getByText('暂无请求记录')).toBeInTheDocument()
  })

  it('renders request rows with timestamps', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const t1 = formatTimeForTest(mockRequests[0].timestamp)
    const t2 = formatTimeForTest(mockRequests[1].timestamp)
    expect(screen.getByText(t1)).toBeInTheDocument()
    expect(screen.getByText(t2)).toBeInTheDocument()
  })

  it('shows model chain for non-fallback request with checkmark', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getAllByText('gpt-4o')).toHaveLength(2)
  })

  it('shows model chain for fallback request with actual model', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    expect(screen.getByText('claude-3-opus')).toBeInTheDocument()
    expect(screen.getByText('claude-3-sonnet')).toBeInTheDocument()
    expect(screen.getByText('claude-3-haiku')).toBeInTheDocument()
  })

  it('marks fallback rows with orange left border', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const rows = screen.getAllByTestId('request-row')
    // First row: no fallback
    expect(rows[0].className).not.toContain('border-orange-400')
    // Second row: fallback
    expect(rows[1].className).toContain('border-orange-400')
  })

  it('displays status code and total tokens', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const statusCodes = screen.getAllByTestId('status-code')
    expect(statusCodes).toHaveLength(3)
    expect(statusCodes[0]).toHaveTextContent('200')
    expect(statusCodes[1]).toHaveTextContent('200')
    expect(statusCodes[2]).toHaveTextContent('200')
    const tokens = screen.getAllByTestId('total-tokens')
    expect(tokens[0]).toHaveTextContent('230')
    expect(tokens[1]).toHaveTextContent('800')
    expect(tokens[2]).toHaveTextContent('150')
  })

  it('expands detail card on click', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const rows = screen.getAllByTestId('request-row')
    fireEvent.click(rows[0])
    expect(screen.getByText('任务类型')).toBeInTheDocument()
    expect(screen.getByText('chat')).toBeInTheDocument()
    expect(screen.getByText('难度')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()
    expect(screen.getByText('策略')).toBeInTheDocument()
    expect(screen.getByText('cost-optimized')).toBeInTheDocument()
    expect(screen.getByText('req-001')).toBeInTheDocument()
  })

  it('collapses detail card on second click', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const rows = screen.getAllByTestId('request-row')
    fireEvent.click(rows[0])
    expect(screen.getByText('任务类型')).toBeInTheDocument()
    fireEvent.click(rows[0])
    expect(screen.queryByText('任务类型')).not.toBeInTheDocument()
  })

  it('shows fallback chain in detail for fallback request', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const rows = screen.getAllByTestId('request-row')
    fireEvent.click(rows[1])
    expect(screen.getByText('fallback 链')).toBeInTheDocument()
    const chainContainer = screen.getByTestId('fallback-chain')
    expect(chainContainer).toHaveTextContent('claude-3-sonnet')
    expect(chainContainer).toHaveTextContent('claude-3-haiku')
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('shows retry badge for requests with retry history', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const retryBadges = screen.getAllByTestId('retry-badge')
    expect(retryBadges).toHaveLength(1)
    expect(retryBadges[0]).toHaveTextContent('↻2')
  })

  it('shows retry history in detail card', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const rows = screen.getAllByTestId('request-row')
    fireEvent.click(rows[2])
    expect(screen.getByText('重试历史')).toBeInTheDocument()
    const historyContainer = screen.getByTestId('retry-history')
    expect(historyContainer).toHaveTextContent('gpt-4o')
    expect(historyContainer).toHaveTextContent('502')
    expect(historyContainer).toHaveTextContent('gpt-4o-mini')
    expect(historyContainer).toHaveTextContent('TimeoutError')
    expect(historyContainer).toHaveTextContent('异常')
  })

  it('does not show retry history section when empty', () => {
    render(<RecentRequestsPanel requests={mockRequests} />)
    const rows = screen.getAllByTestId('request-row')
    fireEvent.click(rows[0])
    expect(screen.queryByText('重试历史')).not.toBeInTheDocument()
  })
})
