import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

const deal = { id: 'aster', company: 'Aster Health', contact: 'Priya', title: 'Pilot',
  stage: 'Discovery', value: 72000, summary: 'Twelve clinics', interactions: [] };
const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });

function mockAPI(handler) {
  const fetch = vi.fn(async (url, options) => {
    if (url === '/api/health') return response({ memory_configured: false });
    if (url === '/api/deals' && options.method === 'GET') return response([deal]);
    return handler(url, options);
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

describe('DealMind dashboard', () => {
  it('loads actual API records, searches, and shows empty results', async () => {
    mockAPI(() => response({}));
    render(<App />);
    expect(await screen.findByText('Twelve clinics')).toBeInTheDocument();
    expect(screen.getByText('Setup needed')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Search deals'), { target: { value: 'missing' } });
    expect(screen.getByText(/No deals match/)).toBeInTheDocument();
  });

  it('surfaces memory errors and clearly labels fallback intelligence', async () => {
    mockAPI(url => url.endsWith('/recall')
      ? response({ detail: 'Hindsight is not configured.' }, 503)
      : response({ mode: 'demo', brief: 'Current CRM context', memories: [], next_actions: ['Confirm pilot'],
        warning: 'Rules-based development brief; not AI-generated.', generated_at: '2026-09-29T00:00:00Z' }));
    render(<App />);
    await screen.findByText('Twelve clinics');
    fireEvent.click(screen.getByRole('button', { name: 'Recall', exact: true }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Hindsight is not configured');
    fireEvent.click(screen.getByRole('button', { name: /Prepare brief/ }));
    expect(await screen.findByText('Rules-based development brief')).toBeInTheDocument();
    expect(screen.getByText('Confirm pilot')).toBeInTheDocument();
  });

  it('saves interaction through backend and shows failed delivery independently', async () => {
    const interaction = { id: 'i1', title: 'SSO review', content: 'Requires SSO', channel: 'Call',
      occurred_at: '2026-09-29T00:00:00Z', memory_status: 'failed', memory_error: 'Service unavailable' };
    const fetch = mockAPI(url => response(url.endsWith('/interactions') ? interaction : { ...deal, interactions: [interaction] }));
    render(<App />);
    await screen.findByText('Twelve clinics');
    fireEvent.click(screen.getByRole('button', { name: /Log interaction/ }));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'SSO review' } });
    fireEvent.change(screen.getByLabelText('Conversation notes'), { target: { value: 'Requires SSO' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save interaction' }));
    expect(await screen.findByText('SSO review')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Interaction saved. Service unavailable');
    expect(fetch.mock.calls.some(([url, options]) => url.endsWith('/interactions') && JSON.parse(options.body).content === 'Requires SSO')).toBe(true);
  });

  it('ignores recall responses from a previously selected deal', async () => {
    let resolveRecall;
    const fetch = mockAPI(() => new Promise(resolve => { resolveRecall = resolve; }));
    fetch.mockImplementation(async (url, options) => {
      if (url === '/api/health') return response({});
      if (url === '/api/deals') return response([deal, { ...deal, id: 'north', company: 'Northstar', summary: 'Fleet context' }]);
      return new Promise(resolve => { resolveRecall = resolve; });
    });
    render(<App />);
    await screen.findByText('Twelve clinics');
    fireEvent.click(screen.getByRole('button', { name: 'Recall', exact: true }));
    fireEvent.click(screen.getByRole('button', { name: /Northstar/ }));
    resolveRecall(response({ memories: [{ id: 'old', text: 'Wrong customer evidence', type: 'world' }] }));
    await waitFor(() => expect(screen.getByText('Fleet context')).toBeInTheDocument());
    expect(screen.queryByText('Wrong customer evidence')).not.toBeInTheDocument();
  });

  it('allows retry after backend loading fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Backend offline')));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend offline');
    mockAPI(() => response({}));
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }));
    expect(await screen.findByText('Twelve clinics')).toBeInTheDocument();
  });
});
