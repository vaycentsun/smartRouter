import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ModelsExplorer } from './ModelsExplorer'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('ModelsExplorer', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.providers = [
      { name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true },
    ]
    mockStoreState.models = [
      { name: 'gpt-4', provider: 'openai', available: true, quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
    ]
    mockStoreState.saveProviders = vi.fn().mockResolvedValue(undefined)
    mockStoreState.isSavingProviders = false
    mockStoreState.toast = null
    mockStoreState.clearToast = vi.fn()
  })

  it('renders sidebar and models panel', () => {
    render(<ModelsExplorer />)
    expect(screen.getAllByText('openai').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
  })

  it('shows empty state when no providers', () => {
    mockStoreState.providers = []
    mockStoreState.models = []
    render(<ModelsExplorer />)
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()
  })
})
