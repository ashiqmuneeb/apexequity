/**
 * Centralized HTTP Client for the Financial Stock Analysis API.
 * Handles base URLs, standard headers, and normalized error throwing.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const ADMIN_API_KEY =
  import.meta.env.VITE_ADMIN_API_KEY ||
  (typeof window !== 'undefined' ? localStorage.getItem('apex_admin_key') : null) ||
  'dev-admin-key';

export async function apiClient(endpoint, options = {}) {
  const { body, headers = {}, ...customConfig } = options;

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  if (ADMIN_API_KEY) {
    defaultHeaders['X-API-Key'] = ADMIN_API_KEY;
  }

  const config = {
    method: body ? 'POST' : 'GET',
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    ...customConfig,
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMessage =
      data?.detail || data?.message || `HTTP ${response.status}: Request failed`;
    throw new Error(errorMessage);
  }

  return data;
}
