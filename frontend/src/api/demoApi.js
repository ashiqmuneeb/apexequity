import { apiClient } from './client';

export const demoApi = {
  getDemo: (name = 'single') => {
    return apiClient(`/api/v1/demo/${name}`);
  },
};

