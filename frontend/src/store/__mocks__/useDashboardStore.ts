import { vi } from 'vitest'

export const mockStoreState: Record<string, unknown> = {
  models: [],
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
  fetchAnalytics: vi.fn().mockResolvedValue(undefined),
  // Playground
  playgroundResults: [],
  playgroundHistory: [],
  isLoadingPlayground: false,
  playgroundError: null,
  runPlayground: vi.fn().mockResolvedValue(undefined),
  fetchPlaygroundHistory: vi.fn().mockResolvedValue(undefined),
  deletePlaygroundHistory: vi.fn().mockResolvedValue(undefined),
  clearPlaygroundError: vi.fn(),
  // Alerts
  alertRules: [],
  alertHistory: [],
  isLoadingAlerts: false,
  alertsError: null,
  fetchAlertRules: vi.fn().mockResolvedValue(undefined),
  createAlertRule: vi.fn().mockResolvedValue(undefined),
  updateAlertRule: vi.fn().mockResolvedValue(undefined),
  deleteAlertRule: vi.fn().mockResolvedValue(undefined),
  fetchAlertHistory: vi.fn().mockResolvedValue(undefined),
  testAlertRule: vi.fn().mockResolvedValue(null),
  clearAlertsError: vi.fn(),
  // Health Check
  isCheckingHealth: {},
  checkProviderHealth: vi.fn().mockResolvedValue(undefined),
}

export const useDashboardStore = vi.fn(() => mockStoreState)
