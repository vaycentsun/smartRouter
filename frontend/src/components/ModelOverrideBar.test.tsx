import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModelOverrideBar } from './ModelOverrideBar'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('ModelOverrideBar', () => {
  beforeEach(() => {
    mockStoreState.modelOverrides = {
      openai: ['gpt-4o', 'gpt-4o-mini'],
      anthropic: ['claude-3', 'claude-2'],
    }
    mockStoreState.modelOverride = { provider: null, model: null, enabled: false }
    mockStoreState.setModelOverride = vi.fn()
    mockStoreState.clearModelOverride = vi.fn()
  })

  it('renders default state with provider options', () => {
    render(<ModelOverrideBar />)
    expect(screen.getByText('使用默认路由')).toBeInTheDocument()
    expect(screen.getByLabelText('选择 Provider')).toBeInTheDocument()
    expect(screen.getByLabelText('选择模型')).toBeInTheDocument()
    expect(screen.getByLabelText('选择模型')).toBeDisabled()
  })

  it('populates model dropdown when provider selected', () => {
    render(<ModelOverrideBar />)
    const providerSelect = screen.getByLabelText('选择 Provider')
    fireEvent.change(providerSelect, { target: { value: 'openai' } })
    expect(mockStoreState.setModelOverride).toHaveBeenCalledWith('openai', 'gpt-4o')
  })

  it('shows enabled state and clear button when override active', () => {
    mockStoreState.modelOverride = { provider: 'openai', model: 'gpt-4o', enabled: true }
    render(<ModelOverrideBar />)
    expect(screen.getByText('覆盖已启用')).toBeInTheDocument()
    expect(screen.getByLabelText('回到默认路由')).toBeInTheDocument()
  })

  it('calls clearModelOverride when clear button clicked', () => {
    mockStoreState.modelOverride = { provider: 'openai', model: 'gpt-4o', enabled: true }
    render(<ModelOverrideBar />)
    fireEvent.click(screen.getByLabelText('回到默认路由'))
    expect(mockStoreState.clearModelOverride).toHaveBeenCalled()
  })

  it('displays override info text when enabled', () => {
    mockStoreState.modelOverride = { provider: 'anthropic', model: 'claude-3', enabled: true }
    render(<ModelOverrideBar />)
    expect(screen.getByText(/路由策略已暂停/)).toBeInTheDocument()
    expect(screen.getByText(/anthropic\/claude-3/)).toBeInTheDocument()
  })
})
