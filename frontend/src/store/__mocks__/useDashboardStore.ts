import { vi } from 'vitest'

export const mockStoreState: Record<string, unknown> = {}

export const useDashboardStore = vi.fn(() => mockStoreState)
