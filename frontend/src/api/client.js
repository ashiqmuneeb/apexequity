/**
 * Centralized HTTP Client for the Financial Stock Analysis API.
 * Handles base URLs, standard headers, and normalized error throwing.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY;

export async function apiClient(endpoint, options = {}) {
  const { body, headers = {}, ...customConfig } = options;

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  if (ADMIN_API_KEY && ADMIN_API_KEY.trim()) {
    defaultHeaders['X-API-Key'] = ADMIN_API_KEY.trim();
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
    const error = new Error(errorMessage);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
