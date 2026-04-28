import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ProviderEditModal } from './ProviderEditModal'
import type { ProviderInfo } from '../types'

const mockProvider: ProviderInfo = {
  name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true, masked_key: 'sk-****',
}

describe('ProviderEditModal', () => {
  it('does not render when closed', () => {
    render(<ProviderEditModal provider={mockProvider} isOpen={false} onClose={vi.fn()} onSave={vi.fn()} isSaving={false} />)
    expect(screen.queryByText('编辑 Provider: openai')).not.toBeInTheDocument()
  })

  it('renders form when open', () => {
    render(<ProviderEditModal provider={mockProvider} isOpen={true} onClose={vi.fn()} onSave={vi.fn()} isSaving={false} />)
    expect(screen.getByText('编辑 Provider: openai')).toBeInTheDocument()
    expect(screen.getByDisplayValue('https://api.openai.com')).toBeInTheDocument()
  })

  it('calls onSave with correct data', () => {
    const onSave = vi.fn()
    render(<ProviderEditModal provider={mockProvider} isOpen={true} onClose={vi.fn()} onSave={onSave} isSaving={false} />)
    fireEvent.change(screen.getByDisplayValue('https://api.openai.com'), { target: { value: 'https://new.api.com' } })
    fireEvent.click(screen.getByText('保存'))
    expect(onSave).toHaveBeenCalledWith('openai', { api_base: 'https://new.api.com', api_key: 'os.environ/OPENAI_API_KEY', timeout: 30 })
  })

  it('calls onClose when cancel clicked', () => {
    const onClose = vi.fn()
    render(<ProviderEditModal provider={mockProvider} isOpen={true} onClose={onClose} onSave={vi.fn()} isSaving={false} />)
    fireEvent.click(screen.getByText('取消'))
    expect(onClose).toHaveBeenCalled()
  })
})
