import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ModelMappingTab } from './ModelMappingTab'
import * as apiModule from '../api/client'

vi.mock('../api/client')

describe('ModelMappingTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no mappings configured', async () => {
    vi.mocked(apiModule.api.getModelMappings).mockResolvedValue({ enabled: false, mappings: [] })
    vi.mocked(apiModule.api.getModelMappingsYaml).mockResolvedValue({ yaml: '' })

    render(<ModelMappingTab />)

    await waitFor(() => {
      expect(screen.getByText('No mappings configured')).toBeInTheDocument()
    })
  })

  it('renders table with rules after loading config', async () => {
    vi.mocked(apiModule.api.getModelMappings).mockResolvedValue({
      enabled: true,
      mappings: [
        {
          id: 'rule-1',
          enabled: true,
          from_model: 'gpt-4',
          to_provider: 'anthropic',
          to_model: 'claude-3-opus',
          to_litellm_provider: 'anthropic',
          to_base_url: 'https://api.anthropic.com',
          to_api_key: '',
          endpoints: ['chat', 'responses'],
        },
      ],
    })
    vi.mocked(apiModule.api.getModelMappingsYaml).mockResolvedValue({ yaml: '- from_model: gpt-4\n  to_model: claude-3-opus\n' })

    render(<ModelMappingTab />)

    await waitFor(() => {
      expect(screen.getByText('gpt-4')).toBeInTheDocument()
    })
    expect(screen.getByText('claude-3-opus')).toBeInTheDocument()
    expect(screen.getByText('anthropic')).toBeInTheDocument()
    expect(screen.getByText('https://api.anthropic.com')).toBeInTheDocument()
  })

  it('switches to YAML editor view', async () => {
    vi.mocked(apiModule.api.getModelMappings).mockResolvedValue({ enabled: false, mappings: [] })
    vi.mocked(apiModule.api.getModelMappingsYaml).mockResolvedValue({ yaml: '' })

    render(<ModelMappingTab />)

    await waitFor(() => {
      expect(screen.getByText('Table View')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('YAML Editor'))

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })
  })

  it('toggles global enabled switch', async () => {
    vi.mocked(apiModule.api.getModelMappings).mockResolvedValue({ enabled: false, mappings: [] })
    vi.mocked(apiModule.api.getModelMappingsYaml).mockResolvedValue({ yaml: '' })

    render(<ModelMappingTab />)

    await waitFor(() => {
      expect(screen.getByText('Global Enabled')).toBeInTheDocument()
    })

    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).not.toBeChecked()

    fireEvent.click(checkbox)

    await waitFor(() => {
      expect(checkbox).toBeChecked()
    })
  })

  it('deletes a rule from the table', async () => {
    vi.mocked(apiModule.api.getModelMappings).mockResolvedValue({
      enabled: true,
      mappings: [
        {
          id: 'rule-1',
          enabled: true,
          from_model: 'gpt-4',
          to_provider: 'anthropic',
          to_model: 'claude-3-opus',
          to_litellm_provider: 'anthropic',
          to_base_url: '',
          to_api_key: '',
          endpoints: ['chat', 'responses'],
        },
      ],
    })
    vi.mocked(apiModule.api.getModelMappingsYaml).mockResolvedValue({ yaml: '' })

    render(<ModelMappingTab />)

    await waitFor(() => {
      expect(screen.getByText('gpt-4')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('DELETE'))

    await waitFor(() => {
      expect(screen.queryByText('gpt-4')).not.toBeInTheDocument()
      expect(screen.getByText('No mappings configured')).toBeInTheDocument()
    })
  })

  it('saves YAML content and triggers API call', async () => {
    vi.mocked(apiModule.api.getModelMappings).mockResolvedValue({ enabled: false, mappings: [] })
    vi.mocked(apiModule.api.getModelMappingsYaml).mockResolvedValue({ yaml: 'enabled: false\n' })
    vi.mocked(apiModule.api.updateModelMappingsYaml).mockResolvedValue({ success: true })

    render(<ModelMappingTab />)

    await waitFor(() => {
      expect(screen.getByText('YAML Editor')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('YAML Editor'))

    const textarea = await waitFor(() => screen.getByRole('textbox'))
    fireEvent.change(textarea, { target: { value: 'enabled: true\nmappings:\n  - from_model: gpt-4\n' } })

    fireEvent.click(screen.getByText('SAVE'))

    await waitFor(() => {
      expect(apiModule.api.updateModelMappingsYaml).toHaveBeenCalledWith('enabled: true\nmappings:\n  - from_model: gpt-4\n')
    })
  })
})
