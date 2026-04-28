/// <reference types="vitest/globals" />

interface GlobalThis {
  confirm(message?: string): boolean
}

declare global {
  const global: GlobalThis
}

export {}