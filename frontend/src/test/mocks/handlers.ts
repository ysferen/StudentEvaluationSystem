import { http, HttpResponse } from 'msw';

// Add per-feature handlers here as tests are introduced.
export const handlers = [
  http.get('*/health', () => HttpResponse.json({ ok: true })),
];
