import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ProvidersTable } from './ProvidersTable'

vi.mock('../store/useDashboardStore')

import { mockStoreState } from '../store/__mocks__/useDashboardStore'

describe('ProvidersTable', () => {
  beforeEach(() => {
    Object.keys(mockStoreState).forEach((k) => delete (mockStoreState as Record<string, unknown>)[k])
    mockStoreState.saveProviders = vi.fn().mockResolvedValue(undefined)
    mockStoreState.isSavingProviders = false
    mockStoreState.toast = null
    mockStoreState.clearToast = vi.fn()
  })

  const sampleProviders = [
    { name: 'openai', api_base: 'https://api.openai.com', timeout: 30, key_type: 'env:OPENAI_API_KEY', has_key: true, masked_key: 'sk-***' },
    { name: 'azure', api_base: 'https://azure.com', timeout: 60, key_type: 'manual', has_key: false },
  ]

  it('shows empty state when no providers', () => {
    mockStoreState.providers = []
    render(<ProvidersTable />)
    expect(screen.getByText('暂无 Provider 数据')).toBeInTheDocument()
  })

  it('initializes edits with env key placeholder', () => {
    mockStoreState.providers = sampleProviders
    render(<ProvidersTable />)
    const inputs = screen.getAllByDisplayValue('os.environ/OPENAI_API_KEY')
    expect(inputs.length).toBeGreaterThan(0)
  })

  it('initializes edits with empty key for non-env type', () => {
    mockStoreState.providers = sampleProviders
    render(<ProvidersTable />)
    // azure has key_type 'manual' and no env prefix, so api_key should be empty
    const keyInput = screen.getByDisplayValue('')
    expect(keyInput).toBeInTheDocument()
  })

  it('marks dirty on api_base change', () => {
    mockStoreState.providers = sampleProviders
    render(<ProvidersTable />)
    const baseInputs = screen.getAllByRole('textbox')
    // First textbox in openai row is api_base
    fireEvent.change(baseInputs[0], { target: { value: 'https://new.openai.com' } })
    // Save button should become enabled after change
    expect(screen.getByText('保存所有修改')).not.toBeDisabled()
  })

  it('calls saveProviders with correct payload on save', async () => {
    mockStoreState.providers = sampleProviders
    render(<ProvidersTable />)
    const baseInputs = screen.getAllByRole('textbox')
    fireEvent.change(baseInputs[0], { target: { value: 'https://new.openai.com' } })

    fireEvent.click(screen.getByText('保存所有修改'))

    await waitFor(() => {
      expect(mockStoreState.saveProviders).toHaveBeenCalledWith(
        expect.objectContaining({
          openai: expect.objectContaining({
            api_base: 'https://new.openai.com',
            timeout: 30,
          }),
        })
      )
    })
  })

  it('does not include api_key in payload unless modified', async () => {
    mockStoreState.providers = sampleProviders
    render(<ProvidersTable />)
    const baseInputs = screen.getAllByRole('textbox')
    // Only change api_base, not api_key
    fireEvent.change(baseInputs[0], { target: { value: 'https://new.openai.com' } })

    fireEvent.click(screen.getByText('保存所有修改'))

    await waitFor(() => {
      const payload = (mockStoreState.saveProviders as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(payload.openai).not.toHaveProperty('api_key')
    })
  })

  it('includes api_key in payload when modified', async () => {
    mockStoreState.providers = sampleProviders
    render(<ProvidersTable />)
    // Change api_key for openai (first provider row)
    const keyInputs = screen.getAllByPlaceholderText('')
    fireEvent.change(keyInputs[0], { target: { value: 'new-key' } })

    fireEvent.click(screen.getByText('保存所有修改'))

    await waitFor(() => {
      const payload = (mockStoreState.saveProviders as ReturnType<typeof vi.fn>).mock.calls[0][0]
      expect(payload.openai.api_key).toBe('new-key')
    })
  })

  it('shows toast message when present', () => {
    mockStoreState.providers = sampleProviders
    mockStoreState.toast = { message: '保存成功', type: 'success' }
    render(<ProvidersTable />)
    expect(screen.getByText('保存成功')).toBeInTheDocument()
  })

  it('auto-clears toast after 3 seconds', () => {
    vi.useFakeTimers()
    mockStoreState.providers = sampleProviders
    mockStoreState.toast = { message: '保存成功', type: 'success' }
    const { unmount } = render(<ProvidersTable />)
    expect(screen.getByText('保存成功')).toBeInTheDocument()

    vi.advanceTimersByTime(3000)
    expect(mockStoreState.clearToast).toHaveBeenCalled()
    unmount()
    vi.useRealTimers()
  })
})
