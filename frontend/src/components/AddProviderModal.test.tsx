import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AddProviderModal } from './AddProviderModal'

function getInputByLabelText(labelText: string): HTMLInputElement {
  const label = screen.getByText(labelText)
  const input = label.parentElement?.querySelector('input')
  if (!input) throw new Error(`No input found for label: ${labelText}`)
  return input as HTMLInputElement
}

describe('AddProviderModal', () => {
  it('renders form fields when open', () => {
    render(<AddProviderModal isOpen={true} onClose={vi.fn()} onSubmit={vi.fn()} isSaving={false} />)
    expect(screen.getByText('NAME')).toBeInTheDocument()
    expect(screen.getByText('API BASE')).toBeInTheDocument()
    expect(screen.getByText('API KEY')).toBeInTheDocument()
    expect(screen.getByText('TIMEOUT')).toBeInTheDocument()
  })

  it('calls onSubmit with correct data when form is valid', () => {
    const onSubmit = vi.fn()
    render(<AddProviderModal isOpen={true} onClose={vi.fn()} onSubmit={onSubmit} isSaving={false} />)

    fireEvent.change(getInputByLabelText('NAME'), { target: { value: 'openai' } })
    fireEvent.change(getInputByLabelText('API BASE'), { target: { value: 'https://api.openai.com' } })
    fireEvent.change(getInputByLabelText('API KEY'), { target: { value: 'sk-test' } })
    fireEvent.change(getInputByLabelText('TIMEOUT'), { target: { value: '60' } })

    fireEvent.click(screen.getByText('CREATE'))

    expect(onSubmit).toHaveBeenCalledWith({
      name: 'openai',
      api_base: 'https://api.openai.com',
      api_key: 'sk-test',
      timeout: 60,
    })
  })

  it('shows error and does not call onSubmit when name is empty', () => {
    const onSubmit = vi.fn()
    render(<AddProviderModal isOpen={true} onClose={vi.fn()} onSubmit={onSubmit} isSaving={false} />)

    fireEvent.change(getInputByLabelText('API BASE'), { target: { value: 'https://api.openai.com' } })
    fireEvent.click(screen.getByText('CREATE'))

    expect(screen.getByText('Name is required')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('does not call onSubmit when timeout is 0', () => {
    const onSubmit = vi.fn()
    render(<AddProviderModal isOpen={true} onClose={vi.fn()} onSubmit={onSubmit} isSaving={false} />)

    fireEvent.change(getInputByLabelText('NAME'), { target: { value: 'openai' } })
    fireEvent.change(getInputByLabelText('API BASE'), { target: { value: 'https://api.openai.com' } })
    fireEvent.change(getInputByLabelText('TIMEOUT'), { target: { value: '0' } })

    fireEvent.click(screen.getByText('CREATE'))

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn()
    render(<AddProviderModal isOpen={true} onClose={onClose} onSubmit={vi.fn()} isSaving={false} />)

    fireEvent.click(screen.getByText('CANCEL'))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when overlay is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(<AddProviderModal isOpen={true} onClose={onClose} onSubmit={vi.fn()} isSaving={false} />)

    const overlay = container.querySelector('.bg-black\\/60')
    expect(overlay).toBeTruthy()
    fireEvent.click(overlay!)
    expect(onClose).toHaveBeenCalled()
  })
})
