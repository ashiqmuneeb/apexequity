import React, { useState, useEffect } from 'react';
import { HelpCircle, Sparkles, Copy, Check, ChevronDown, ChevronUp, FileText, Cpu, ShieldAlert, Activity, ArrowUpRight } from 'lucide-react';
import { analysisApi } from '../../api/analysisApi';
import MarkdownView from '../../components/common/MarkdownView';
import LoadingSkeleton from '../../components/common/LoadingSkeleton';
import ErrorCard from '../../components/common/ErrorCard';
import { SAMPLE_QUESTIONS } from '../../constants/stockTickers';

export default function CustomQueryView({ onOpenKeyModal, initialPrompt = '' }) {
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

  const handleRunPreset = async (queryText) => {
    setPrompt(queryText);
    setLoading(true);
    setError(null);
    try {
      const data = await analysisApi.customQuery(queryText);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!result?.report) return;
    navigator.clipboard.writeText(result.report);
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
              Whole SEC Corpus
            </span>
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Query across the full indexed library of Form 10-K disclosures, balance sheets, and management commentary.
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
                  <span>Ask AI</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error Card */}
      <ErrorCard
        title="Query Error"
        message={error}
        onConfigureKey={onOpenKeyModal}
      />

      {/* Loading Skeleton */}
      {loading && <LoadingSkeleton text="Synthesizing multi-filing evidence across institutional corpus..." />}

      {/* Initial Empty State: Clean Suggested Inquiries */}
      {!result && !loading && (
        <div className="space-y-4 animate-fade-in">
          <div className="pt-2">
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              Macro Research Topics
            </h3>
            <p className="text-xs text-slate-600">
              Run multi-company vector retrieval across all filed Form 10-K disclosures.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="terminal-card bg-white border border-slate-200 hover:border-[#01257D]/50 hover:shadow-lg rounded-xl p-5 transition flex flex-col justify-between group shadow-xs">
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-bold text-[#01257D] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    Hardware & Cloud
                  </span>
                  <Cpu className="h-4 w-4 text-slate-400" />
                </div>
                <h4 className="text-sm font-bold text-slate-900 group-hover:text-[#01257D] transition mb-1.5">
                  Hyperscale CapEx Cycle
                </h4>
                <p className="text-xs text-slate-600 leading-relaxed mb-4">
                  Aggregates disclosures across NVIDIA, Google, and Microsoft regarding AI infrastructure spend and chip orders.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleRunPreset(SAMPLE_QUESTIONS[2])}
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-blue-50 hover:bg-[#01257D] text-[#01257D] hover:text-white border border-blue-200 text-xs font-semibold transition cursor-pointer shadow-xs"
              >
                <span>Analyze CapEx</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="terminal-card bg-white border border-slate-200 hover:border-[#01257D]/50 hover:shadow-lg rounded-xl p-5 transition flex flex-col justify-between group shadow-xs">
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                    Legal & Antitrust
                  </span>
                  <ShieldAlert className="h-4 w-4 text-rose-500" />
                </div>
                <h4 className="text-sm font-bold text-slate-900 group-hover:text-rose-600 transition mb-1.5">
                  Antitrust & Export Controls
                </h4>
                <p className="text-xs text-slate-600 leading-relaxed mb-4">
                  Surfaces all legal proceedings, Department of Justice inquiries, and export restrictions across covered firms.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleRunPreset(SAMPLE_QUESTIONS[1])}
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-rose-50 hover:bg-rose-600 text-rose-700 hover:text-white border border-rose-200 text-xs font-semibold transition cursor-pointer shadow-xs"
              >
                <span>Audit Risks</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="terminal-card bg-white border border-slate-200 hover:border-[#01257D]/50 hover:shadow-lg rounded-xl p-5 transition flex flex-col justify-between group shadow-xs">
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-bold text-[#01257D] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    Cloud Infrastructure
                  </span>
                  <Activity className="h-4 w-4 text-slate-400" />
                </div>
                <h4 className="text-sm font-bold text-slate-900 group-hover:text-[#01257D] transition mb-1.5">
                  Cloud Revenue Growth
                </h4>
                <p className="text-xs text-slate-600 leading-relaxed mb-4">
                  Contrasts Google Cloud and Microsoft Azure revenue expansion, operating profit, and enterprise adoption.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleRunPreset(SAMPLE_QUESTIONS[0])}
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-blue-50 hover:bg-[#01257D] text-[#01257D] hover:text-white border border-blue-200 text-xs font-semibold transition cursor-pointer shadow-xs"
              >
                <span>Compare Cloud</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

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
                  <span>Audited Filing Citations ({result.sources.length} Verified Sources)</span>
                </div>
                {showSources ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showSources && (
                <div className="mt-4 space-y-3">
                  {result.sources.map((src, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-xs">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="font-mono text-[#01257D] font-bold">SEC Disclosure Excerpt #{i + 1}</span>
                        {src.score && (
                          <span className="text-[11px] text-[#01257D] font-mono bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-bold">
                            Confidence Match: {(src.score * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                      <p className="text-slate-700 leading-relaxed font-mono text-[11px] bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                        {src.text}
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
