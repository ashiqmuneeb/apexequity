import React, { useState, useEffect } from 'react';
import { HelpCircle, Sparkles, Copy, Check, ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { analysisApi } from '../../api/analysisApi';
import MarkdownView from '../../components/common/MarkdownView';
import LoadingSkeleton from '../../components/common/LoadingSkeleton';
import ErrorCard from '../../components/common/ErrorCard';
import InfoTooltip from '../../components/common/InfoTooltip';
import { SAMPLE_QUESTIONS } from '../../constants/stockTickers';

export default function CustomQueryView({ onOpenKeyModal, initialPrompt = '', onGoToFilings }) {
  const [prompt, setPrompt] = useState(initialPrompt || '');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  useEffect(() => {
    if (initialPrompt) {
      setPrompt(initialPrompt);
    }
  }, [initialPrompt]);

  const handleQuery = async (e) => {
    if (e) e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await analysisApi.customQuery(prompt.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!result?.report) return;
    const textToCopy = `${result.report}\n\n*ApexEquity is for informational and educational research purposes only. Not investment advice.*`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      
      {/* Control Card on Matte White */}
      <div className="terminal-card bg-white border border-slate-200 rounded-xl p-5 shadow-xs relative overflow-hidden backdrop-blur-md">
        <div className="mb-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span>Ask AI Assistant</span>
            <span className="text-[11px] font-bold text-[#01257D] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 shadow-xs">
              Document Corpus
            </span>
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Query across the full indexed library of financial disclosures, balance sheets, and management commentary.
          </p>
        </div>

        {/* Preset Questions */}
        <div className="mb-3.5">
          <span className="text-xs text-slate-500 font-semibold block mb-2">Example Inquiries:</span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SAMPLE_QUESTIONS.map((q, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setPrompt(q)}
                className="text-left p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs text-slate-700 hover:text-slate-900 transition cursor-pointer flex items-start gap-2 shadow-xs"
              >
                <HelpCircle className="h-3.5 w-3.5 text-[#01257D] shrink-0 mt-0.5" />
                <span className="line-clamp-2">{q}</span>
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleQuery} className="space-y-3">
          <div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask any financial, market, or corporate governance question across the filing universe..."
              rows={3}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] transition"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="h-10 px-5 bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] hover:opacity-95 text-white font-bold text-sm rounded-xl shadow-md transition cursor-pointer disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Synthesizing Filings...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-cyan-200" />
                  <span>Execute Inquiry</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error Presentation */}
      {error && (
        <ErrorCard
          title="Inquiry Execution Error"
          message={error}
          onRetry={handleQuery}
          onConfigureKey={onOpenKeyModal}
          onGoToFilings={onGoToFilings}
        />
      )}

      {/* Loading Skeleton */}
      {loading && <LoadingSkeleton text="Scanning vector storage & synthesizing cited answers from disclosures..." />}

      {/* Result Presentation Card */}
      {result && !loading && (
        <div className="terminal-card bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden">
          
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#01257D]" />
              <span>Executive Intelligence Briefing</span>
            </h3>

            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer shadow-xs"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          <div className="p-6 sm:p-8">
            <MarkdownView content={result.report} />

            <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-500 text-center mt-4">
              ApexEquity is for informational and educational research purposes only and does not constitute financial, legal, or investment advice.
            </div>
          </div>

          {/* Sources Section */}
          {result.sources && result.sources.length > 0 && (
            <div className="border-t border-slate-200 bg-slate-50/80 p-6">
              <button
                type="button"
                onClick={() => setShowSources(!showSources)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-700 hover:text-[#01257D] transition cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-[#01257D]" />
                  <span>Context Evidence Passages ({result.sources.length} Verified Sources)</span>
                </div>
                {showSources ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showSources && (
                <div className="mt-4 space-y-3">
                  {result.sources.map((src, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-slate-500 font-mono text-[10px]">
                        <span className="text-[#01257D] font-bold">
                          Citation [{i + 1}] &bull; {src.ticker || src.metadata?.ticker || ''} &bull; {src.section || src.metadata?.section || 'Item 1'} ({src.form || '10-K'} FY{src.fiscal_year || src.metadata?.fiscal_year || ''})
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-[#01257D] font-mono bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-bold">
                            #{src.rank || i + 1}
                          </span>
                          {src.rerank_score != null && (
                            <InfoTooltip title="rerank score" text={src.rerank_score.toFixed(3)} />
                          )}
                        </div>
                      </div>
                      {src.accession_number && (
                        <div className="text-[10px] text-slate-500 font-mono">
                          Accession: {src.accession_number}
                        </div>
                      )}
                      <p className="text-slate-700 leading-relaxed font-mono text-[11px] bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                        {src.quote || src.text}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      )}

    </div>
  );
}
