/**
 * Type guard: checks if a value is a non-null object (Record).
 * Used for safely narrowing unknown API responses.
 */
export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
