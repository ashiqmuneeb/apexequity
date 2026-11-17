import React, { useState } from 'react';
import { Folder, Plus, Trash2, Eye, RefreshCw, FileText, Check, X, Globe, Sparkles } from 'lucide-react';
import { useArticles } from '../../hooks/useArticles';
import { articlesApi } from '../../api/articlesApi';
import ErrorCard from '../../components/common/ErrorCard';

export default function ArticleManager({ onRebuildIndex, isRebuilding, onCorpusChange }) {
  const {
    articles,
    loading,
    error,
    setError,
    successMsg,
    setSuccessMsg,
    saveArticle,
    deleteArticle,
    fetchArticles,
  } = useArticles(onCorpusChange);

  // Live Fetch state
  const [liveTicker, setLiveTicker] = useState('');
  const [fetchingLive, setFetchingLive] = useState(false);

  // New Article Form state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTicker, setNewTicker] = useState('');
  const [newContent, setNewContent] = useState('');
  const [saving, setSaving] = useState(false);

  // View Article modal
  const [viewingArticle, setViewingArticle] = useState(null);

  const handleFetchLive = async (tickerToFetch) => {
    const symbol = (tickerToFetch || liveTicker).trim().toUpperCase();
    if (!symbol) return;

    setFetchingLive(true);
    setError(null);
    try {
      const data = await articlesApi.fetchLiveStock(symbol);
      setSuccessMsg(
        `Fetched live financials for ${data.company_name} ($${data.ticker}) • Revenue: ${data.revenue || 'N/A'} • Indexed into vector storage.`
      );
      setLiveTicker('');
      await fetchArticles();
      if (onCorpusChange) onCorpusChange();
    } catch (err) {
      setError(err.message || `Failed to fetch live data for ${symbol}`);
    } finally {
      setFetchingLive(false);
    }
  };

  const handleSaveArticle = async (e) => {
    e.preventDefault();
    if (!newTicker.trim() || !newContent.trim()) return;

    setSaving(true);
    try {
      await saveArticle(newTicker.trim().toUpperCase(), newContent.trim());
      setShowAddModal(false);
      setNewTicker('');
      setNewContent('');
    } catch {
      // Error handled inside hook
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (ticker) => {
    if (!window.confirm(`Delete article for ${ticker}?`)) return;
    try {
      await deleteArticle(ticker);
    } catch {
      // Error handled inside hook
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner on Matte White */}
      <div className="terminal-card bg-white border border-slate-200 rounded-xl p-5 shadow-xs backdrop-blur-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Folder className="h-4.5 w-4.5 text-[#01257D]" />
            <span>Financial Document Library</span>
            <span className="text-[11px] font-bold text-[#01257D] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 shadow-xs">
              {articles.length} Indexed
            </span>
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Filing disclosures, balance sheets, and reports vectorized into local storage.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] text-white hover:opacity-95 text-xs font-semibold transition cursor-pointer shadow-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Filing</span>
          </button>

          <button
            onClick={onRebuildIndex}
            disabled={isRebuilding}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer disabled:opacity-50 shadow-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRebuilding ? 'animate-spin text-[#01257D]' : 'text-[#01257D]'}`} />
            <span>{isRebuilding ? 'Syncing...' : 'Sync Filings'}</span>
          </button>
        </div>
      </div>

      {/* Live Market Ingestion Card */}
      <div className="terminal-card bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-[#01257D]" />
              <h3 className="text-sm font-bold text-slate-900">Live Stock Ingestion</h3>
            </div>
            <p className="text-xs text-slate-600">
              Fetch market overview and corporate financials for any US public equity.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-slate-500 mr-1 font-medium">Quick Ingest:</span>
            {['TSLA', 'AMZN', 'META', 'AMD'].map((t) => (
              <button
                key={t}
                onClick={() => handleFetchLive(t)}
                disabled={fetchingLive}
                className="px-2 py-0.5 rounded-md text-xs font-mono font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-[#01257D] border border-slate-200 transition cursor-pointer disabled:opacity-50 shadow-xs"
              >
                +${t}
              </button>
            ))}
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleFetchLive();
          }}
          className="mt-3.5 flex flex-col sm:flex-row gap-2"
        >
          <div className="relative flex-1">
            <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 font-mono text-xs">
              $
            </span>
            <input
              type="text"
              value={liveTicker}
              onChange={(e) => setLiveTicker(e.target.value.toUpperCase())}
              placeholder="Enter ANY Ticker (e.g. NFLX, BRK-B, INTC, CRM)..."
              disabled={fetchingLive}
              className="w-full pl-8 pr-4 h-10 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] transition"
            />
          </div>

          <button
            type="submit"
            disabled={fetchingLive || !liveTicker.trim()}
            className="h-10 px-5 bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] hover:opacity-95 text-white font-semibold text-xs rounded-xl shadow-xs transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            {fetchingLive ? (
              <>
                <div className="h-3.5 w-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Fetching...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5 text-cyan-200" />
                <span>Ingest & Index</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <Check className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 hover:text-emerald-900 cursor-pointer">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {error && <ErrorCard title="Corpus Error" message={error} />}

      {/* Clean Grid of Indexed Filings */}
      {articles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Indexed Filings ({articles.length})</span>
            <span className="font-mono text-[11px]">Storage: ./articles &bull; Local CPU Embeddings</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {articles.map((art) => (
              <div
                key={art.ticker}
                className="terminal-card bg-white border border-slate-200 hover:border-[#01257D]/50 hover:shadow-lg rounded-xl p-5 transition flex flex-col justify-between group shadow-xs"
              >
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="px-2.5 py-0.5 rounded-md bg-blue-50 text-[#01257D] font-mono font-bold text-xs border border-blue-200 shadow-xs">
                      ${art.ticker}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {(art.length / 1024).toFixed(1)} KB &bull; {art.length.toLocaleString()} chars
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-slate-900 mb-2">
                    {art.filename}
                  </h4>

                  <p className="text-xs text-slate-700 line-clamp-3 font-mono leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200 mb-3.5">
                    {art.preview}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-200 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => setViewingArticle(art)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-[#01257D] hover:text-white bg-blue-50 hover:bg-[#01257D] border border-blue-200 transition cursor-pointer shadow-xs"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>View Filing</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDelete(art.ticker)}
                    className="p-1.5 rounded-lg text-xs font-medium text-rose-600 hover:text-rose-700 hover:bg-rose-50 transition cursor-pointer"
                    title={`Delete ${art.ticker}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {articles.length === 0 && !loading && (
        <div className="text-center py-12 bg-white border border-dashed border-slate-300 rounded-2xl shadow-xs">
          <FileText className="h-10 w-10 text-slate-400 mx-auto mb-3" />
          <p className="text-sm text-slate-700 font-medium">No articles currently in corpus.</p>
          <p className="text-xs text-slate-500 mt-1">Add a new company filing to begin vectorizing.</p>
        </div>
      )}

      {/* Add Article Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg shadow-2xl p-6 relative">
            <button
              onClick={() => setShowAddModal(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>

            <h3 className="text-base font-bold text-slate-900 mb-1">Deposit Filing or Financial Note</h3>
            <p className="text-xs text-slate-600 mb-4">
              Enter the ticker symbol and paste 10-K/10-Q disclosures, earnings call transcripts, or equity research notes.
            </p>

            <form onSubmit={handleSaveArticle} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Stock Ticker Symbol
                </label>
                <input
                  type="text"
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                  placeholder="e.g. TSLA, AMZN, META"
                  required
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Filing Text (Form 10-K / 10-Q / Earnings Transcript)
                </label>
                <textarea
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="Paste financial summary, revenue figures, margin changes, growth drivers, and risk factors..."
                  rows={8}
                  required
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D]"
                />
              </div>

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-600 hover:bg-slate-100 transition cursor-pointer font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !newTicker.trim() || !newContent.trim()}
                  className="px-5 py-2 rounded-xl text-xs font-semibold text-white bg-[#01257D] hover:bg-[#0244c9] transition shadow-md disabled:opacity-50 cursor-pointer"
                >
                  {saving ? 'Committing...' : 'Commit to Filing Repository'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Article Modal */}
      {viewingArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl p-6 relative">
            <button
              onClick={() => setViewingArticle(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <span className="px-3 py-1 rounded-lg bg-blue-50 text-[#01257D] font-bold font-mono text-sm border border-blue-200 shadow-xs">
                ${viewingArticle.ticker}
              </span>
              <h3 className="text-base font-bold text-slate-900">{viewingArticle.filename}</h3>
            </div>

            <div className="flex-1 overflow-y-auto bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-800 font-mono leading-relaxed whitespace-pre-wrap">
              {viewingArticle.content}
            </div>

            <div className="flex justify-end pt-4">
              <button
                type="button"
                onClick={() => setViewingArticle(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 transition cursor-pointer border border-slate-200 shadow-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
