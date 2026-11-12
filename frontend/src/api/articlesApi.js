import { apiClient } from './client';

export const articlesApi = {
  /**
   * Fetch all stored corporate documents and notes.
   */
  listArticles: () => {
    return apiClient('/api/articles');
  },

  /**
   * Save or upload a new financial report for a ticker.
   */
  saveArticle: (ticker, content) => {
    return apiClient('/api/articles', {
      body: { ticker, content },
    });
  },

  /**
   * Delete an article file.
   */
  deleteArticle: (ticker) => {
    return apiClient(`/api/articles/${ticker}`, {
      method: 'DELETE',
    });
  },

  /**
   * Automatically fetch real-time market filings via Yahoo Finance and embed.
   */
  fetchLiveStock: (ticker) => {
    return apiClient('/api/articles/fetch-live', {
      body: { ticker },
    });
  },

  /**
   * Trigger vector index rebuilding.
   */
  rebuildIndex: () => {
    return apiClient('/api/index/rebuild', {
      method: 'POST',
    });
  },
};

