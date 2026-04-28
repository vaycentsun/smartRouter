import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Header } from './Header'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('Header', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.fetchAll = vi.fn().mockResolvedValue(undefined)
    mockStoreState.stopService = vi.fn().mockResolvedValue(undefined)
    mockStoreState.clearError = vi.fn()
    mockStoreState.isLoading = false
    vi.stubGlobal('confirm', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders title', () => {
    render(<Header />)
    expect(screen.getByText('Smart Router Dashboard')).toBeInTheDocument()
  })

  it('calls fetchAll when refresh button clicked', () => {
    render(<Header />)
    fireEvent.click(screen.getByText('刷新'))
    expect(mockStoreState.clearError).toHaveBeenCalled()
    expect(mockStoreState.fetchAll).toHaveBeenCalled()
  })

  it('disables buttons when loading', () => {
    mockStoreState.isLoading = true
    render(<Header />)
    expect(screen.getByText('刷新中...')).toBeDisabled()
    expect(screen.getByText('停止服务')).toBeDisabled()
  })

  it('calls stopService when stop confirmed', async () => {
    ;(global.confirm as ReturnType<typeof vi.fn>).mockReturnValue(true)
    render(<Header />)
    fireEvent.click(screen.getByText('停止服务'))
    expect(global.confirm).toHaveBeenCalledWith('确定要停止 Smart Router 服务吗？')
    expect(mockStoreState.stopService).toHaveBeenCalled()
  })

  it('does not call stopService when cancelled', () => {
    ;(global.confirm as ReturnType<typeof vi.fn>).mockReturnValue(false)
    render(<Header />)
    fireEvent.click(screen.getByText('停止服务'))
    expect(mockStoreState.stopService).not.toHaveBeenCalled()
  })
})
