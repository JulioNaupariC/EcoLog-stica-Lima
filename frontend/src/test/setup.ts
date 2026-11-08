import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// jsdom has no layout engine; overflow callbacks are driven explicitly in UI tests.
vi.stubGlobal('ResizeObserver', class {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
})

afterEach(() => {
  cleanup()
})
