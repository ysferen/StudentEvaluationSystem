import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { server } from './mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))

// Cleanup after each test
afterEach(() => {
  server.resetHandlers()
  cleanup()
})

afterAll(() => server.close())

// Suppress ApexCharts errors in test environment
const originalError = console.error
console.error = (...args) => {
  if (typeof args[0] === 'string' && args[0].includes('Getting bbox of element')) {
    return // Suppress ApexCharts SVG errors
  }
  originalError.call(console, ...args)
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
globalThis.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
} as any

// Mock ResizeObserver
globalThis.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any

// Mock getBBox for SVG elements (for ApexCharts)
const SVGMock = SVGElement as any
SVGMock.prototype.getBBox = vi.fn(() => ({
  x: 0,
  y: 0,
  width: 100,
  height: 100,
}))
