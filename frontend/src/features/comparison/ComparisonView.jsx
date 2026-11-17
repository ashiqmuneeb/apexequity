import React, { useState } from 'react';
import { GitCompare, Copy, Check, Download, ChevronDown, ChevronUp, FileText, ArrowLeftRight, Printer, Zap, Award } from 'lucide-react';
import { analysisApi } from '../../api/analysisApi';
import { demoApi } from '../../api/demoApi';
import MarkdownView from '../../components/common/MarkdownView';
import LoadingSkeleton from '../../components/common/LoadingSkeleton';
import ErrorCard from '../../components/common/ErrorCard';
import ComparisonChart from '../../components/common/ComparisonChart';
import { DEFAULT_TICKERS } from '../../constants/stockTickers';

const FEATURED_MATCHUPS = [
  {
    stockA: 'NVDA',
    stockB: 'GOOGL',
    title: 'Hardware Compute Moat vs Search & Cloud Scale',
    thesis: 'Compares NVIDIA GPU silicon dominance with Alphabet diversified search advertising and Gemini AI foundation model integration.',
    tag: 'Benchmark Matchup',
    tagColor: 'text-[#01257D] bg-blue-50 border-blue-200',
  },
  {
    stockA: 'AAPL',
    stockB: 'MSFT',
    title: 'Consumer Hardware Ecosystem vs Enterprise Cloud',
    thesis: 'Evaluates Apple device installed base and Services margins against Microsoft Azure infrastructure and commercial Copilot seats.',
    tag: 'Platform Benchmark',
    tagColor: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  },
  {
    stockA: 'GOOGL',
    stockB: 'MSFT',
    title: 'Hyperscale Cloud & Generative AI Infrastructure',
    thesis: 'Direct comparison between Google Cloud Platform and Microsoft Azure in enterprise workload migrations and foundation model APIs.',
    tag: 'Hyperscaler Benchmark',
    tagColor: 'text-indigo-700 bg-indigo-50 border-indigo-200',
  },
];

export default function ComparisonView({ availableTickers = [], onOpenKeyModal }) {
  const [stockA, setStockA] = useState('NVDA');
  const [stockB, setStockB] = useState('GOOGL');
  const [customPromptEnabled, setCustomPromptEnabled] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const handleSwap = () => {
    const temp = stockA;
    setStockA(stockB);
    setStockB(temp);
  };

  const handleLoadDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await demoApi.getDemo('compare');
      setStockA(data.stock_a || 'NVDA');
      setStockB(data.stock_b || 'GOOGL');
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to load comparison demo');
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async (e, overrideA, overrideB) => {
    if (e && e.preventDefault) e.preventDefault();
    const targetA = (overrideA || stockA).trim();
    const targetB = (overrideB || stockB).trim();
    if (!targetA || !targetB) return;

    setLoading(true);
    setError(null);

    try {
      const data = await analysisApi.compareStocks(
        targetA.toUpperCase(),
        targetB.toUpperCase(),
        customPromptEnabled && customPrompt.trim() ? customPrompt.trim() : null
      );
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

  const handleDownload = () => {
    if (!result?.report) return;
    const disclaimer = '\n\n---\n*ApexEquity is for informational and educational research purposes only. Not investment advice.*';
    const blob = new Blob([result.report + disclaimer], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.stock_a}_vs_${result.stock_b}_Comparative_Analysis.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const quickTickers = availableTickers?.length > 0 ? availableTickers : DEFAULT_TICKERS;

  return (
    <div className="space-y-6">
      
      {/* Control Card on Matte White */}
      <div className="terminal-card bg-white border border-slate-200 rounded-xl p-5 shadow-xs relative overflow-hidden backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>Dual-Issuer Comparative Analysis</span>
              <span className="text-[11px] font-bold text-[#01257D] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 shadow-xs">
                Audited Disclosures
              </span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Side-by-side benchmarking of revenue trajectories, margin structures, and strategic risk factors.
            </p>
          </div>

          <button
            type="button"
            onClick={handleLoadDemo}
            className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-[#01257D] border border-blue-200 text-xs font-semibold transition cursor-pointer shadow-xs"
          >
            <Zap className="h-3.5 w-3.5 text-[#01257D]" />
            <span>Load Sample (NVDA vs GOOGL)</span>
          </button>
        </div>

        <form onSubmit={handleCompare} className="space-y-3.5">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <label className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1">
                Primary Security ($A)
              </label>
              <input
                type="text"
                value={stockA}
                onChange={(e) => setStockA(e.target.value.toUpperCase())}
                placeholder="e.g. NVDA"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 font-mono font-bold placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] uppercase tracking-wider transition"
              />
            </div>

            <button
              type="button"
              onClick={handleSwap}
              title="Swap primary and comparison securities"
              className="mt-4 sm:mt-5 p-2.5 rounded-xl border border-slate-300 hover:border-[#01257D] bg-slate-50 hover:bg-white text-slate-600 hover:text-[#01257D] transition cursor-pointer shadow-xs"
            >
              <ArrowLeftRight className="h-4 w-4" />
            </button>

            <div className="relative flex-1 w-full">
              <label className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1">
                Benchmark Security ($B)
              </label>
              <input
                type="text"
                value={stockB}
                onChange={(e) => setStockB(e.target.value.toUpperCase())}
                placeholder="e.g. GOOGL"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 font-mono font-bold placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] uppercase tracking-wider transition"
              />
            </div>

            <div className="w-full sm:w-auto mt-4 sm:mt-5">
              <button
                type="submit"
                disabled={loading || !stockA.trim() || !stockB.trim()}
                className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-white bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] hover:opacity-95 transition shadow-sm disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
              >
                <GitCompare className="h-4 w-4" />
                <span>{loading ? 'Synthesizing...' : 'Compare'}</span>
              </button>
            </div>
          </div>

          {/* Quick Select Buttons */}
          <div className="flex items-center gap-2 pt-0.5 flex-wrap">
            <span className="text-[11px] text-slate-500 font-medium">Quick Fill:</span>
            {quickTickers.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => {
                  if (stockA !== t) setStockB(t);
                  else setStockA(t);
                }}
                className="text-xs px-2 py-0.5 rounded-lg border font-mono font-semibold bg-slate-50 text-slate-700 hover:text-slate-900 border-slate-200 hover:border-[#01257D]/40 transition cursor-pointer shadow-xs"
              >
                ${t}
              </button>
            ))}
          </div>

          {/* Custom Prompt Toggle */}
          <div className="pt-2 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setCustomPromptEnabled(!customPromptEnabled)}
              className="text-xs text-slate-600 hover:text-[#01257D] flex items-center gap-1 font-semibold transition cursor-pointer"
            >
              {customPromptEnabled ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              <span>{customPromptEnabled ? 'Hide Custom Prompt Parameters' : 'Customize Query Focus (Optional)'}</span>
            </button>

            {customPromptEnabled && (
              <div className="mt-2.5">
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="e.g. Focus specifically on cloud margin comparison, operating leverage, and generative AI monetization."
                  rows={2}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-300 rounded-xl text-slate-800 placeholder-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] transition"
                />
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Featured Matchup Cards (When no report) */}
      {!result && !loading && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex items-center justify-between">
            <h3 className="text-xs uppercase font-bold tracking-wider text-slate-600">
              Institutional Head-to-Head Benchmarks
            </h3>
            <span className="text-[11px] text-slate-500">1-click synthesis</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {FEATURED_MATCHUPS.map((matchup, idx) => (
              <div
                key={idx}
                className="terminal-card bg-white border border-slate-200 rounded-xl p-4.5 flex flex-col justify-between hover:border-blue-400 hover:shadow-md transition shadow-xs group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-1.5 font-mono font-bold text-xs text-[#01257D]">
                      <span className="bg-blue-50 px-2 py-0.5 rounded border border-blue-200 shadow-xs">${matchup.stockA}</span>
                      <span className="text-slate-400 text-[10px]">vs</span>
                      <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">${matchup.stockB}</span>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${matchup.tagColor}`}>
                      {matchup.tag}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-slate-900 mb-1.5 group-hover:text-[#01257D] transition">
                    {matchup.title}
                  </h4>
                  <p className="text-[11px] text-slate-600 leading-relaxed mb-3">
                    {matchup.thesis}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setStockA(matchup.stockA);
                    setStockB(matchup.stockB);
                    handleCompare(null, matchup.stockA, matchup.stockB);
                  }}
                  className="w-full py-1.5 px-3 rounded-lg bg-blue-50 hover:bg-blue-100 text-[#01257D] border border-blue-200 text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <span>Run Comparison</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Presentation */}
      {error && (
        <ErrorCard
          title="Comparative Evaluation Error"
          message={error}
          onRetry={() => handleCompare(null, stockA, stockB)}
          onOpenKeyModal={onOpenKeyModal}
        />
      )}

      {/* Loading Skeleton */}
      {loading && <LoadingSkeleton text="Synthesizing side-by-side filing statements, operating ratios & margin disclosures..." />}

      {/* Result Presentation Card */}
      {result && !loading && (
        <div className="terminal-card bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden animate-fade-in">
          
          {/* Header Bar */}
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5 font-mono font-bold text-sm">
                <span className="bg-blue-50 text-[#01257D] px-2.5 py-1 rounded-lg border border-blue-200 shadow-xs">
                  ${result.stock_a}
                </span>
                <span className="text-slate-400 font-sans text-xs">vs</span>
                <span className="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-lg border border-slate-200 shadow-xs">
                  ${result.stock_b}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 hidden sm:inline">Comparative Research Benchmark</h3>
              {result.is_sample && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border border-amber-300 bg-amber-50 text-amber-800 shadow-xs">
                  Sample data
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer shadow-xs"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copied ? 'Copied' : 'Full Text'}</span>
              </button>

              <button
                type="button"
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer shadow-xs"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Export .md</span>
              </button>

              <button
                type="button"
                onClick={() => window.print()}
                title="Print or Save as PDF"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer shadow-xs"
              >
                <Printer className="h-3.5 w-3.5" />
                <span>Print</span>
              </button>
            </div>
          </div>

          {/* Report Body */}
          <div className="p-6 sm:p-8 space-y-6">
            {result.comparison_metrics && result.comparison_metrics.length > 0 && (
              <div className="space-y-5">
                {/* Visual Comparative Chart */}
                <div className="w-full">
                  <ComparisonChart
                    data={result.comparison_metrics}
                    stockA={result.stock_a}
                    stockB={result.stock_b}
                    className="h-full"
                  />
                </div>

                {/* Head-to-Head Quantitative Delta Tile */}
                <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Award className="h-4 w-4 text-[#01257D]" />
                      <h4 className="text-xs uppercase font-bold tracking-wider text-slate-800">
                        Disclosed Financial Delta Comparison
                      </h4>
                    </div>
                    <span className="text-[10px] text-[#01257D] font-mono font-bold bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 shadow-xs">
                      Disclosed Metrics
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {result.comparison_metrics.map((item, idx) => {
                      const valA = item[result.stock_a];
                      const valB = item[result.stock_b];
                      const numA = Number(valA) || 0;
                      const numB = Number(valB) || 0;
                      const leader = numA >= numB ? result.stock_a : result.stock_b;
                      const hasValues = valA !== null && valA !== undefined && valB !== null && valB !== undefined;

                      return (
                        <div key={idx} className="bg-white p-3.5 rounded-xl border border-slate-200 hover:border-blue-300 transition shadow-xs">
                          <div className="flex items-center justify-between text-xs mb-2">
                            <span className="text-slate-700 font-bold truncate">{item.metric}</span>
                            {hasValues && (
                              <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${
                                leader === result.stock_a 
                                  ? 'bg-blue-50 text-[#01257D] border-blue-200' 
                                  : 'bg-slate-100 text-slate-800 border-slate-200'
                              }`}>
                                ${leader} Leads
                              </span>
                            )}
                          </div>
                          <div className="flex items-center justify-between font-mono text-xs pt-1 border-t border-slate-100">
                            <div className="text-slate-700">
                              <span className="text-[#01257D] font-bold">${result.stock_a}:</span> {valA !== null && valA !== undefined ? valA : 'N/A'}
                            </div>
                            <div className="text-slate-400 text-[10px] font-sans">&bull;</div>
                            <div className="text-slate-700">
                              <span className="text-slate-600 font-bold">${result.stock_b}:</span> {valB !== null && valB !== undefined ? valB : 'N/A'}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="pt-3 border-t border-slate-200 mt-4 text-[10px] text-slate-500 font-mono flex items-center justify-between">
                    <span>Comparative Financial Benchmark</span>
                    <span className="text-[#01257D] font-bold">Grounded Filing Comparison</span>
                  </div>
                </div>
              </div>
            )}

            <MarkdownView content={result.report} />

            {/* Disclaimer at bottom of report */}
            <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-500 text-center">
              ApexEquity is for informational and educational research purposes only and does not constitute financial, legal, or investment advice.
            </div>

          </div>

          {/* Sources Section */}
          {result.sources && result.sources.length > 0 && (
            <div className="border-t border-slate-200 px-6 py-4 bg-slate-50">
              <button
                type="button"
                onClick={() => setShowSources(!showSources)}
                className="flex items-center justify-between w-full text-xs font-semibold text-slate-700 hover:text-slate-900 transition cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-[#01257D]" />
                  <span>Audited Context Passages &amp; Evidence ({result.sources.length} Chunks)</span>
                </span>
                {showSources ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showSources && (
                <div className="mt-3 space-y-2">
                  {result.sources.map((src, i) => (
                    <div
                      key={i}
                      className="p-3 bg-white rounded-lg border border-slate-200 text-xs text-slate-700 space-y-1 shadow-xs"
                    >
                      <div className="flex items-center justify-between font-mono text-[10px] text-slate-500">
                        <span className="font-bold text-[#01257D]">Citation [{i + 1}]</span>
                        {src.score != null && (
                          <span className="bg-blue-50 text-[#01257D] px-2 py-0.5 rounded border border-blue-200 font-bold">
                            Score: {src.score.toFixed(3)}
                          </span>
                        )}
                      </div>
                      <p className="font-mono text-[11px] leading-relaxed text-slate-800">
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
