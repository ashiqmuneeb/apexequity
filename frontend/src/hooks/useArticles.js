import { useState, useEffect, useCallback } from 'react';
import { articlesApi } from '../api/articlesApi';

export function useArticles(onCorpusChange) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await articlesApi.listArticles();
      setArticles(data.articles || []);
    } catch (err) {
      setError(err.message || 'Failed to load articles');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  const saveArticle = async (ticker, content) => {
    setError(null);
    try {
      const data = await articlesApi.saveArticle(ticker, content);
      setSuccessMsg(`Saved article for $${ticker.toUpperCase()}. Click "Re-Index" to embed into vector store.`);
      await fetchArticles();
      if (onCorpusChange) onCorpusChange();
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const deleteArticle = async (ticker) => {
    setError(null);
    try {
      await articlesApi.deleteArticle(ticker);
      setSuccessMsg(`Deleted article for $${ticker.toUpperCase()}`);
      await fetchArticles();
      if (onCorpusChange) onCorpusChange();
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  return {
    articles,
    loading,
    error,
    setError,
    successMsg,
    setSuccessMsg,
    fetchArticles,
    saveArticle,
    deleteArticle,
  };
}

