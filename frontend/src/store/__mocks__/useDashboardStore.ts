import { vi } from 'vitest'

export const mockStoreState: Record<string, unknown> = {
  modelOverrides: {},
  modelOverride: { provider: null, model: null, enabled: false },
  setModelOverride: vi.fn(),
  clearModelOverride: vi.fn(),
  tokenStats: [],
}

export const useDashboardStore = vi.fn(() => mockStoreState)
