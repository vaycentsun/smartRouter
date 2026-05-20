import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AddModelModal } from './AddModelModal'

describe('AddModelModal', () => {
  it('does not render when closed', () => {
    render(<AddModelModal providerName="openai" isOpen={false} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    expect(screen.queryByText('添加模型: openai')).not.toBeInTheDocument()
  })

  it('renders form fields when open', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    expect(screen.getByText('添加模型: openai')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('模型名称')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('litellm 模型名称')).toBeInTheDocument()
    expect(screen.getByLabelText('质量')).toBeInTheDocument()
    expect(screen.getByLabelText('成本')).toBeInTheDocument()
    expect(screen.getByLabelText('上下文')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('chat,code,embedding')).toBeInTheDocument()
    expect(screen.getByLabelText('启用')).toBeInTheDocument()
  })

  it('calls onSubmit with parsed data when form is valid', () => {
    const onSubmit = vi.fn()
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={onSubmit} isSaving={false} />)
    
    fireEvent.change(screen.getByPlaceholderText('模型名称'), { target: { value: 'gpt-4' } })
    fireEvent.change(screen.getByPlaceholderText('litellm 模型名称'), { target: { value: 'openai/gpt-4' } })
    fireEvent.change(screen.getByLabelText('质量'), { target: { value: '9' } })
    fireEvent.change(screen.getByLabelText('成本'), { target: { value: '8' } })
    fireEvent.change(screen.getByLabelText('上下文'), { target: { value: '128000' } })
    fireEvent.change(screen.getByPlaceholderText('chat,code,embedding'), { target: { value: 'chat,code' } })
    
    fireEvent.click(screen.getByText('添加'))
    
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'gpt-4',
      litellm_model: 'openai/gpt-4',
      quality: 9,
      cost: 8,
      context: 128000,
      supported_tasks: ['chat', 'code'],
      enabled: true,
    })
  })

  it('calls onClose when cancel clicked', () => {
    const onClose = vi.fn()
    render(<AddModelModal providerName="openai" isOpen={true} onClose={onClose} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.click(screen.getByText('取消'))
    expect(onClose).toHaveBeenCalled()
  })

  it('shows validation error when name is empty', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.click(screen.getByText('添加'))
    expect(screen.getByText('名称不能为空')).toBeInTheDocument()
  })

  it('shows validation error when litellm_model is empty', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.change(screen.getByPlaceholderText('模型名称'), { target: { value: 'gpt-4' } })
    fireEvent.click(screen.getByText('添加'))
    expect(screen.getByText('LiteLLM 模型不能为空')).toBeInTheDocument()
  })

  it('shows validation error when quality is out of range', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.change(screen.getByPlaceholderText('模型名称'), { target: { value: 'gpt-4' } })
    fireEvent.change(screen.getByPlaceholderText('litellm 模型名称'), { target: { value: 'openai/gpt-4' } })
    fireEvent.change(screen.getByLabelText('质量'), { target: { value: '15' } })
    fireEvent.click(screen.getByText('添加'))
    expect(screen.getByText('质量必须在 1-10 之间')).toBeInTheDocument()
  })

  it('shows validation error when cost is out of range', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.change(screen.getByPlaceholderText('模型名称'), { target: { value: 'gpt-4' } })
    fireEvent.change(screen.getByPlaceholderText('litellm 模型名称'), { target: { value: 'openai/gpt-4' } })
    fireEvent.change(screen.getByLabelText('成本'), { target: { value: '0' } })
    fireEvent.click(screen.getByText('添加'))
    expect(screen.getByText('成本必须在 1-10 之间')).toBeInTheDocument()
  })

  it('shows validation error when context is not positive', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.change(screen.getByPlaceholderText('模型名称'), { target: { value: 'gpt-4' } })
    fireEvent.change(screen.getByPlaceholderText('litellm 模型名称'), { target: { value: 'openai/gpt-4' } })
    fireEvent.change(screen.getByLabelText('上下文'), { target: { value: '0' } })
    fireEvent.click(screen.getByText('添加'))
    expect(screen.getByText('上下文必须为正整数')).toBeInTheDocument()
  })

  it('shows validation error when supported_tasks is empty', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    fireEvent.change(screen.getByPlaceholderText('模型名称'), { target: { value: 'gpt-4' } })
    fireEvent.change(screen.getByPlaceholderText('litellm 模型名称'), { target: { value: 'openai/gpt-4' } })
    fireEvent.change(screen.getByPlaceholderText('chat,code,embedding'), { target: { value: '' } })
    fireEvent.click(screen.getByText('添加'))
    expect(screen.getByText('至少需要一个支持的任务类型')).toBeInTheDocument()
  })

  it('disables submit button when isSaving is true', () => {
    render(<AddModelModal providerName="openai" isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={true} />)
    expect(screen.getByText('添加中...')).toBeInTheDocument()
    expect(screen.getByText('添加中...')).toBeDisabled()
  })
})
