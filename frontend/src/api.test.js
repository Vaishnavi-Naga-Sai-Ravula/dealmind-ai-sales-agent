import { it, expect, vi } from 'vitest';
import { api } from './api';

it('explains FastAPI validation failures', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422,
    json: async () => ({ detail: [{ loc: ['body', 'title'], msg: 'Field required' }] }) }));
  await expect(api('/deals', {})).rejects.toThrow('title: Field required');
});

it('handles non-JSON server errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502,
    json: async () => { throw new Error('HTML error page'); } }));
  await expect(api('/deals')).rejects.toThrow('Server returned an invalid response (502)');
});
