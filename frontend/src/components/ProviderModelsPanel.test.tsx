import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProviderModelsPanel } from './ProviderModelsPanel'
import type { ModelInfo, ProviderInfo } from '../types'

const mockProvider: ProviderInfo = {
  name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true,
}

const mockModels: ModelInfo[] = [
  { name: 'gpt-4', provider: 'openai', available: true, quality: 10, cost: 4, context: 8192, supported_tasks: ['chat', 'completion'] },
  { name: 'gpt-3.5', provider: 'openai', available: true, quality: 8, cost: 6, context: 4096, supported_tasks: ['chat'] },
  { name: 'claude-3', provider: 'anthropic', available: true, quality: 10, cost: 4, context: 200000, supported_tasks: ['chat'] },
]

describe('ProviderModelsPanel', () => {
  it('shows placeholder when no provider selected', () => {
    render(<ProviderModelsPanel provider={null} models={[]} onEdit={vi.fn()} />)
    expect(screen.getByText('请选择一个 Provider')).toBeInTheDocument()
  })

  it('renders models for selected provider', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={vi.fn()} />)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('gpt-3.5')).toBeInTheDocument()
    expect(screen.queryByText('claude-3')).not.toBeInTheDocument()
  })

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn()
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={onEdit} />)
    fireEvent.click(screen.getByText('编辑配置'))
    expect(onEdit).toHaveBeenCalled()
  })

  it('shows empty state when provider has no models', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={[]} onEdit={vi.fn()} />)
    expect(screen.getByText('该 Provider 暂无模型数据')).toBeInTheDocument()
  })
})
