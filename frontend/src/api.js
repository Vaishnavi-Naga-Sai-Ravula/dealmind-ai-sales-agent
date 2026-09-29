const BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
export const API_DOCS_URL = `${BASE_URL || 'http://127.0.0.1:8000'}/docs`;

export async function api(path, body, signal) {
  const response = await fetch(`${BASE_URL}/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal,
  });
  let data;
  try { data = await response.json(); } catch { throw new Error(`Server returned an invalid response (${response.status}).`); }
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map(item => `${item.loc.at(-1)}: ${item.msg}`).join('; ')
      : data.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}
