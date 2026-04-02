import { describe, expect, it } from 'vitest';
import { customInstance } from '../shared/api/mutator';

describe('MSW integration', () => {
  it('returns mocked response for API request', async () => {
    const response = await customInstance<{ ok: boolean }>({
      url: '/health',
      method: 'GET',
    });

    expect(response).toEqual({ ok: true });
  });
});
