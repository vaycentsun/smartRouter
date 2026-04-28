import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusCard } from './StatusCard'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('StatusCard', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
  })

  it('shows loading when status is null', () => {
    mockStoreState.status = null
    render(<StatusCard />)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('renders running status with uptime', () => {
    mockStoreState.status = {
      running: true,
      pid: 1234,
      uptime_seconds: 3900,
      service_url: 'http://localhost:4000',
      version: '1.2.3',
    }
    render(<StatusCard />)
    expect(screen.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByText('1234')).toBeInTheDocument()
    expect(screen.getByText('1h 5m')).toBeInTheDocument()
    expect(screen.getByText('http://localhost:4000')).toBeInTheDocument()
    expect(screen.getByText('1.2.3')).toBeInTheDocument()
  })

  it('renders stopped status without pid/uptime', () => {
    mockStoreState.status = {
      running: false,
      pid: null,
      uptime_seconds: null,
      service_url: null,
      version: '0.0.1',
    }
    render(<StatusCard />)
    expect(screen.getByText('已停止')).toBeInTheDocument()
    expect(screen.queryByText('PID')).not.toBeInTheDocument()
    expect(screen.queryByText('已运行')).not.toBeInTheDocument()
    expect(screen.getByText('0.0.1')).toBeInTheDocument()
  })

  it('formats uptime as minutes only when under an hour', () => {
    mockStoreState.status = {
      running: true,
      pid: 1,
      uptime_seconds: 45 * 60,
      service_url: 'http://localhost:4000',
      version: '1.0.0',
    }
    render(<StatusCard />)
    expect(screen.getByText('45m')).toBeInTheDocument()
  })

  it('shows dash for null uptime', () => {
    mockStoreState.status = {
      running: true,
      pid: 1,
      uptime_seconds: null,
      service_url: 'http://localhost:4000',
      version: '1.0.0',
    }
    render(<StatusCard />)
    expect(screen.getByText('-')).toBeInTheDocument()
  })
})
