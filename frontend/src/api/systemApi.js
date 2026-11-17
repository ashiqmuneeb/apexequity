import { apiClient } from './client';

export const systemApi = {
  /**
   * Get server health, vector storage state, and Groq key status.
   */
  getStatus: () => {
    return apiClient('/api/v1/status');
  },
};
