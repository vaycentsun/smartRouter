import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProviderSidebar } from './ProviderSidebar'
import type { ProviderInfo } from '../types'

const mockProviders: ProviderInfo[] = [
  { name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true, masked_key: 'sk-****' },
  { name: 'anthropic', api_base: 'https://api.anthropic.com', timeout: 30, key_type: 'env:ANTHROPIC_API_KEY', has_key: false },
]

describe('ProviderSidebar', () => {
  it('renders provider list', () => {
    render(<ProviderSidebar providers={mockProviders} selectedProvider={null} modelsCount={{}} onSelect={vi.fn()} />)
    expect(screen.getByText('openai')).toBeInTheDocument()
    expect(screen.getByText('anthropic')).toBeInTheDocument()
  })

  it('calls onSelect when provider is clicked', () => {
    const onSelect = vi.fn()
    render(<ProviderSidebar providers={mockProviders} selectedProvider={null} modelsCount={{}} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('openai'))
    expect(onSelect).toHaveBeenCalledWith('openai')
  })

  it('shows empty state when no providers', () => {
    render(<ProviderSidebar providers={[]} selectedProvider={null} modelsCount={{}} onSelect={vi.fn()} />)
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()
  })

  it('shows model count', () => {
    render(
      <ProviderSidebar
        providers={mockProviders}
        selectedProvider={null}
        modelsCount={{ openai: 5, anthropic: 2 }}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByText('5 模型')).toBeInTheDocument()
    expect(screen.getByText('2 模型')).toBeInTheDocument()
  })

  it('highlights selected provider', () => {
    render(
      <ProviderSidebar
        providers={mockProviders}
        selectedProvider="openai"
        modelsCount={{}}
        onSelect={vi.fn()}
      />
    )
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBe(2)
  })
})
