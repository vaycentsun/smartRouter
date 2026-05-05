import { vi } from 'vitest'

export const mockStoreState: Record<string, unknown> = {
  modelOverrides: {},
  modelOverride: { provider: null, model: null, enabled: false },
  setModelOverride: vi.fn(),
  clearModelOverride: vi.fn(),
  tokenStats: [],
  analyticsSummary: null,
  analyticsDaily: [],
  analyticsByModel: [],
  analyticsTopModels: [],
  isLoadingAnalytics: false,
  analyticsError: null,
  fetchAnalytics: vi.fn(),
}

export const useDashboardStore = vi.fn(() => mockStoreState)
