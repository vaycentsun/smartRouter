import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProviderModelsPanel } from './ProviderModelsPanel'
import type { ModelInfo, ProviderInfo } from '../types'

const mockProvider: ProviderInfo = {
  name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true,
}

const mockProviderWithDirectKey: ProviderInfo = {
  name: 'anthropic', api_base: 'https://api.anthropic.com', timeout: 30, key_type: 'direct', has_key: true, masked_key: 'sk-ant-***abcd',
}

const mockProviderWithoutKey: ProviderInfo = {
  name: 'moonshot', api_base: 'https://api.moonshot.cn', timeout: 30, key_type: 'direct', has_key: false,
}

const mockModels: ModelInfo[] = [
  { name: 'gpt-4', provider: 'openai', available: true, health_status: 'available', quality: 10, cost: 4, context: 8192, supported_tasks: ['chat', 'completion'], enabled: true },
  { name: 'gpt-3.5', provider: 'openai', available: true, health_status: 'available', quality: 8, cost: 6, context: 4096, supported_tasks: ['chat'], enabled: true },
  { name: 'claude-3', provider: 'anthropic', available: true, health_status: 'available', quality: 10, cost: 4, context: 200000, supported_tasks: ['chat'], enabled: false },
]

describe('ProviderModelsPanel', () => {
  it('shows placeholder when no provider selected', () => {
    render(<ProviderModelsPanel provider={null} models={[]} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByText('请选择一个 Provider')).toBeInTheDocument()
  })

  it('renders models for selected provider', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
    expect(screen.getByText('gpt-3.5')).toBeInTheDocument()
    expect(screen.queryByText('claude-3')).not.toBeInTheDocument()
  })

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn()
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={onEdit} onSaveKey={vi.fn()} isSaving={false} />)
    fireEvent.click(screen.getByText('编辑配置'))
    expect(onEdit).toHaveBeenCalled()
  })

  it('shows empty state when provider has no models', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={[]} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByText('该 Provider 暂无模型数据')).toBeInTheDocument()
  })

  it('shows env key as read-only', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByText('通过环境变量配置（env:OPENAI_API_KEY）')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/sk-/)).not.toBeInTheDocument()
  })

  it('shows masked key placeholder for direct key', () => {
    render(<ProviderModelsPanel provider={mockProviderWithDirectKey} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    const input = screen.getByPlaceholderText('sk-ant-***abcd')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'password')
  })

  it('shows unset placeholder when no key', () => {
    render(<ProviderModelsPanel provider={mockProviderWithoutKey} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    const input = screen.getByPlaceholderText('未设置')
    expect(input).toBeInTheDocument()
    expect(screen.getByText('输入 Key 并保存以启用该 Provider')).toBeInTheDocument()
  })

  it('calls onSaveKey with new key value', () => {
    const onSaveKey = vi.fn()
    render(<ProviderModelsPanel provider={mockProviderWithDirectKey} models={mockModels} onEdit={vi.fn()} onSaveKey={onSaveKey} isSaving={false} />)
    const input = screen.getByPlaceholderText('sk-ant-***abcd')
    fireEvent.change(input, { target: { value: 'sk-new-key' } })
    fireEvent.click(screen.getByText('保存'))
    expect(onSaveKey).toHaveBeenCalledWith('sk-new-key')
  })

  it('calls onSaveKey with empty string when clearing key', () => {
    const onSaveKey = vi.fn()
    render(<ProviderModelsPanel provider={mockProviderWithDirectKey} models={mockModels} onEdit={vi.fn()} onSaveKey={onSaveKey} isSaving={false} />)
    fireEvent.click(screen.getByText('保存'))
    expect(onSaveKey).toHaveBeenCalledWith('')
  })

  it('toggles key visibility', () => {
    render(<ProviderModelsPanel provider={mockProviderWithDirectKey} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    const input = screen.getByPlaceholderText('sk-ant-***abcd')
    expect(input).toHaveAttribute('type', 'password')
    fireEvent.click(screen.getByTitle('显示'))
    expect(input).toHaveAttribute('type', 'text')
  })

  it('disables save button when saving', () => {
    render(<ProviderModelsPanel provider={mockProviderWithDirectKey} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={true} />)
    const btn = screen.getByText('保存中...')
    expect(btn).toBeDisabled()
  })

  // Health Check Tests
  it('shows health check button when onCheckHealth is provided', () => {
    render(
      <ProviderModelsPanel
        provider={mockProvider}
        models={mockModels}
        onEdit={vi.fn()}
        onSaveKey={vi.fn()}
        isSaving={false}
        onCheckHealth={vi.fn()}
      />
    )
    expect(screen.getByText('检查连通性')).toBeInTheDocument()
  })

  it('does not show health check button when onCheckHealth is not provided', () => {
    render(<ProviderModelsPanel provider={mockProvider} models={mockModels} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.queryByText('检查连通性')).not.toBeInTheDocument()
  })

  it('calls onCheckHealth when check button clicked', () => {
    const onCheckHealth = vi.fn()
    render(
      <ProviderModelsPanel
        provider={mockProvider}
        models={mockModels}
        onEdit={vi.fn()}
        onSaveKey={vi.fn()}
        isSaving={false}
        onCheckHealth={onCheckHealth}
      />
    )
    fireEvent.click(screen.getByText('检查连通性'))
    expect(onCheckHealth).toHaveBeenCalledWith('openai')
  })

  it('shows checking state when isCheckingHealth is true', () => {
    render(
      <ProviderModelsPanel
        provider={mockProvider}
        models={mockModels}
        onEdit={vi.fn()}
        onSaveKey={vi.fn()}
        isSaving={false}
        onCheckHealth={vi.fn()}
        isCheckingHealth={true}
      />
    )
    expect(screen.getByText('检测中...')).toBeInTheDocument()
    const btn = screen.getByText('检测中...').closest('button')
    expect(btn).toBeDisabled()
  })

  it('shows available status for healthy model', () => {
    const singleModel: ModelInfo[] = [
      { name: 'gpt-4', provider: 'openai', available: true, health_status: 'available', quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
    ]
    render(<ProviderModelsPanel provider={mockProvider} models={singleModel} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByTitle('该模型在 Provider 端确认可用')).toBeInTheDocument()
  })

  it('shows not_found status for model not in provider list', () => {
    const models: ModelInfo[] = [
      { name: 'gpt-4', provider: 'openai', available: true, health_status: 'not_found', quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
    ]
    render(<ProviderModelsPanel provider={mockProvider} models={models} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByTitle('Provider 返回的模型列表中未找到此模型')).toBeInTheDocument()
  })

  it('shows auth_error status for invalid key', () => {
    const models: ModelInfo[] = [
      { name: 'gpt-4', provider: 'openai', available: true, health_status: 'auth_error', quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
    ]
    const provider: ProviderInfo = {
      ...mockProvider,
      health: { status: 'auth_error', checked_at: 1714972800 },
    }
    render(<ProviderModelsPanel provider={provider} models={models} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByTitle('API Key 无效或权限不足')).toBeInTheDocument()
  })

  it('shows unconfigured status when no key', () => {
    const models: ModelInfo[] = [
      { name: 'gpt-4', provider: 'moonshot', available: false, health_status: 'unconfigured', quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
    ]
    render(<ProviderModelsPanel provider={mockProviderWithoutKey} models={models} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByTitle('API Key 未配置')).toBeInTheDocument()
  })

  it('shows fallback status when health_status is unknown', () => {
    const models: ModelInfo[] = [
      { name: 'gpt-4', provider: 'openai', available: true, health_status: 'unknown', quality: 10, cost: 4, context: 8192, supported_tasks: ['chat'] },
    ]
    render(<ProviderModelsPanel provider={mockProvider} models={models} onEdit={vi.fn()} onSaveKey={vi.fn()} isSaving={false} />)
    expect(screen.getByTitle('健康检查失败')).toBeInTheDocument()
  })
})
