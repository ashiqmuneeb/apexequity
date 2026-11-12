import { apiClient } from './client';

export const analysisApi = {
  /**
   * Run single stock deep dive research report.
   */
  singleStock: (ticker, customPrompt = null, groqApiKey = null) => {
    return apiClient('/api/analyze/single', {
      body: {
        ticker,
        custom_prompt: customPrompt,
        groq_api_key: groqApiKey,
      },
    });
  },

  /**
   * Run competitive multi-stock comparative analysis.
   */
  compareStocks: (stockA, stockB, customPrompt = null, groqApiKey = null) => {
    return apiClient('/api/analyze/compare', {
      body: {
        stock_a: stockA,
        stock_b: stockB,
        custom_prompt: customPrompt,
        groq_api_key: groqApiKey,
      },
    });
  },

  /**
   * Run natural language custom inquiry across the financial corpus.
   */
  customQuery: (prompt, groqApiKey = null) => {
    return apiClient('/api/analyze/custom', {
      body: {
        prompt,
        groq_api_key: groqApiKey,
      },
    });
  },
};

