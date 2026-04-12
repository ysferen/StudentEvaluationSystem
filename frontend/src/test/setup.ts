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
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null
  readonly rootMargin = ''
  readonly thresholds: ReadonlyArray<number> = []

  constructor(_callback: IntersectionObserverCallback) {}
  disconnect() {}
  observe(_target: Element) {}
  takeRecords() {
    return []
  }
  unobserve(_target: Element) {}
}

globalThis.IntersectionObserver = MockIntersectionObserver

// Mock ResizeObserver
class MockResizeObserver implements ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {}
  disconnect() {}
  observe(_target: Element, _options?: ResizeObserverOptions) {}
  unobserve(_target: Element) {}
}

globalThis.ResizeObserver = MockResizeObserver

// Mock getBBox for SVG elements (for ApexCharts)
const svgPrototype = SVGElement.prototype as unknown as { getBBox?: () => DOMRect }
svgPrototype.getBBox = vi.fn(() => ({
  x: 0,
  y: 0,
  width: 100,
  height: 100,
})) as () => DOMRect
