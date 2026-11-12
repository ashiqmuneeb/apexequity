import { useState, useEffect, useCallback } from 'react';
import { systemApi } from '../api/systemApi';
import { articlesApi } from '../api/articlesApi';

export function useSystemStatus() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [rebuildFeedback, setRebuildFeedback] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await systemApi.getStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const saveGroqKey = async (newKey) => {
    await systemApi.saveGroqKey(newKey);
    await fetchStatus();
  };

  const rebuildIndex = async () => {
    setIsRebuilding(true);
    setRebuildFeedback(null);
    try {
      const data = await articlesApi.rebuildIndex();
      setRebuildFeedback({
        type: 'success',
        text: `Indexed ${data.document_chunks} chunk(s) across ${data.indexed_files?.length || 0} files.`,
      });
      await fetchStatus();
    } catch (err) {
      setRebuildFeedback({
        type: 'error',
        text: err.message || 'Failed to rebuild index.',
      });
    } finally {
      setIsRebuilding(false);
      setTimeout(() => setRebuildFeedback(null), 4000);
    }
  };

  return {
    status,
    loading,
    isKeyModalOpen,
    setIsKeyModalOpen,
    isRebuilding,
    rebuildFeedback,
    fetchStatus,
    saveGroqKey,
    rebuildIndex,
  };
}

