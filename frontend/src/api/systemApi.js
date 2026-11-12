import { apiClient } from './client';

export const systemApi = {
  /**
   * Get server health, vector storage state, and Groq key status.
   */
  getStatus: () => {
    return apiClient('/api/status');
  },

  /**
   * Update Groq API key in server memory and .env.
   */
  saveGroqKey: (groqApiKey) => {
    return apiClient('/api/config/key', {
      body: { groq_api_key: groqApiKey },
    });
  },
};

