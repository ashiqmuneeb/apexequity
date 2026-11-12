/**
 * Centralized HTTP Client for the Financial Stock Analysis API.
 * Handles base URLs, standard headers, and normalized error throwing.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export async function apiClient(endpoint, options = {}) {
  const { body, headers = {}, ...customConfig } = options;

  const config = {
    method: body ? 'POST' : 'GET',
    headers: {
      'Content-Type': 'application/json',
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
    const errorMessage = data?.detail || data?.message || `HTTP ${response.status}: Request failed`;
    throw new Error(errorMessage);
  }

  return data;
}

