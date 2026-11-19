import React, { useState, useEffect } from 'react';
import { Copy, Check, Download, ChevronDown, ChevronUp, FileText, Printer, ClipboardList, Zap, ArrowUp } from 'lucide-react';
import { analysisApi } from '../../api/analysisApi';
import { demoApi } from '../../api/demoApi';
import MarkdownView from '../../components/common/MarkdownView';
import LoadingSkeleton from '../../components/common/LoadingSkeleton';
import ErrorCard from '../../components/common/ErrorCard';
import MetricsScorecard from '../../components/common/MetricsScorecard';
import GrowthMarginScorecard from '../../components/common/GrowthMarginScorecard';
import FollowUpQuestions from '../../components/common/FollowUpQuestions';
import InfoTooltip from '../../components/common/InfoTooltip';
import MarketCommandCenter from '../../components/common/MarketCommandCenter';
import { DEFAULT_TICKERS } from '../../constants/stockTickers';

export default function SingleStockView({
  availableTickers = [],
  selectedTicker = '',
  onOpenKeyModal,
  onNavigateCustom,
  onGoToFilings,
}) {
  const [ticker, setTicker] = useState(selectedTicker || 'NVDA');
  const [customPromptEnabled, setCustomPromptEnabled] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [summaryCopied, setSummaryCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    if (selectedTicker && selectedTicker.trim()) {
      setTicker(selectedTicker.trim().toUpperCase());
    }
  }, [selectedTicker]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 350);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const quickTickers = availableTickers?.length > 0 ? availableTickers : DEFAULT_TICKERS;

  const handleGenerate = async (e, tickerOverride) => {
    if (e && e.preventDefault) e.preventDefault();
    const targetTicker = (tickerOverride || ticker).trim();
    if (!targetTicker) return;

    setLoading(true);
    setError(null);

    try {
      const data = await analysisApi.singleStock(
        targetTicker.toUpperCase(),
        customPromptEnabled && customPrompt.trim() ? customPrompt.trim() : null
      );
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await demoApi.getDemo('single');
      setTicker(data.ticker || 'NVDA');
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to load demo data');
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

  const handleCopySummary = () => {
    if (!result) return;
    const summaryText =
      `ApexEquity Research Briefing: $${result.ticker}\n` +
      `• Reported Revenue: ${result.metrics?.revenue_label || (result.metrics?.revenue ? '$' + result.metrics.revenue + 'B' : 'N/A')}\n` +
      `• YoY Growth: ${result.metrics?.growth_label || (result.metrics?.growth_yoy ? '+' + result.metrics.growth_yoy + '%' : 'N/A')}\n` +
      `• Gross Margin: ${result.metrics?.margin_label || (result.metrics?.gross_margin ? result.metrics.gross_margin + '%' : 'N/A')}\n` +
      `• Core Driver: ${result.metrics?.primary_driver || 'N/A'}\n` +
      `• Investment Outlook: ${result.sentiment || 'N/A'}\n\n` +
      `*ApexEquity is for informational and educational research purposes only. Not investment advice.*`;
    navigator.clipboard.writeText(summaryText);
    setSummaryCopied(true);
    setTimeout(() => setSummaryCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!result?.report) return;
    const disclaimer = '\n\n---\n*ApexEquity is for informational and educational research purposes only. Not investment advice.*';
    const blob = new Blob([result.report + disclaimer], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.ticker}_Financial_Analysis_Report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      
      {/* Control Card on Matte White */}
      <div className="terminal-card bg-white border border-slate-200 rounded-xl p-5 shadow-xs relative overflow-hidden backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>Automated Equity Research Dossier</span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Synthesizes balance sheets, operating margins, risk factors, and forward guidance with citations.
            </p>
          </div>

          <button
            type="button"
            onClick={handleLoadDemo}
            className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-[#01257D] border border-blue-200 text-xs font-semibold transition cursor-pointer shadow-xs"
          >
            <Zap className="h-3.5 w-3.5 text-[#01257D]" />
            <span>Load Sample ($NVDA)</span>
          </button>
        </div>

        <form onSubmit={handleGenerate} className="space-y-3.5">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Ticker symbol (e.g. NVDA, MSFT, AAPL)"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 font-mono font-bold placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] uppercase tracking-wider transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !ticker.trim()}
              className="px-6 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-white bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] hover:opacity-95 transition shadow-sm disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
            >
              <span>{loading ? 'Synthesizing...' : 'Synthesize Report'}</span>
            </button>
          </div>

          {/* Quick Select Buttons */}
          <div className="flex items-center gap-2 pt-0.5 flex-wrap">
            <span className="text-[11px] text-slate-500 font-medium">Quick Select:</span>
            {quickTickers.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => {
                  setTicker(t);
                  handleGenerate(null, t);
                }}
                className={`text-xs px-2.5 py-1 rounded-lg border font-mono font-bold transition cursor-pointer shadow-xs ${
                  ticker === t
                    ? 'bg-[#01257D] text-white border-[#01257D]'
                    : 'bg-slate-50 text-slate-700 hover:text-slate-900 border-slate-200 hover:border-[#01257D]/40'
                }`}
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
                  placeholder="e.g. Focus specifically on enterprise AI server shipments, gross margin pressures, and supply chain bottlenecks."
                  rows={2}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-300 rounded-xl text-slate-800 placeholder-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] transition"
                />
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Error Presentation */}
      {error && (
        <ErrorCard
          title="Analysis Generation Error"
          message={error}
          onRetry={() => handleGenerate(null, ticker)}
          onConfigureKey={onOpenKeyModal}
          onGoToFilings={onGoToFilings}
        />
      )}

      {/* Loading Skeleton */}
      {loading && <LoadingSkeleton text="Synthesizing balance sheet trajectory, operating margins & forward guidance..." />}

      {/* Initial Empty State: Executive Market Command Center */}
      {!result && !loading && (
        <MarketCommandCenter
          onSelectStock={(s) => setTicker(s)}
          onQuickAnalyze={(s) => {
            setTicker(s);
            handleGenerate(null, s);
          }}
          onLaunchDemo={handleLoadDemo}
        />
      )}

      {/* Sticky Document Toolbar for Long Reports */}
      {result && !loading && isScrolled && (
        <div className="sticky top-16 z-30 bg-white/90 backdrop-blur-md border border-slate-200/90 shadow-md rounded-2xl px-5 py-2.5 flex items-center justify-between gap-3 animate-slide-down">
          <div className="flex items-center gap-2.5">
            <span className="font-mono font-bold text-xs bg-blue-50 text-[#01257D] px-2.5 py-1 rounded-md border border-blue-200">
              ${result.ticker}
            </span>
            <span className="text-xs font-bold text-slate-900 hidden sm:inline">
              Financial Analysis
            </span>
            {result.is_sample && (
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border border-amber-300 bg-amber-50 text-amber-800">
                Sample data
              </span>
            )}
          </div>

          {/* Quick Jump Anchors */}
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-medium text-slate-600">
            <a href="#section-metrics" className="hover:text-[#01257D] px-2 py-0.5 rounded transition">KPIs</a>
            <span className="text-slate-300">&bull;</span>
            <a href="#section-report" className="hover:text-[#01257D] px-2 py-0.5 rounded transition">Dossier</a>
            <span className="text-slate-300">&bull;</span>
            <a href="#section-inquiries" className="hover:text-[#01257D] px-2 py-0.5 rounded transition">Inquiries</a>
            <span className="text-slate-300">&bull;</span>
            <a href="#section-sources" className="hover:text-[#01257D] px-2 py-0.5 rounded transition">Filings</a>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopySummary}
              className="px-2.5 py-1 rounded-full bg-blue-50 hover:bg-blue-100 text-[#01257D] border border-blue-200 text-xs font-semibold transition cursor-pointer"
            >
              Briefing
            </button>
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="p-1 rounded-full bg-slate-100 hover:bg-slate-200 text-[#01257D] border border-slate-200 transition cursor-pointer"
              title="Back to Top"
            >
              <ArrowUp className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Result Presentation Card */}
      {result && !loading && (
        <div className="terminal-card bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden animate-fade-in">
          
          {/* Header Bar */}
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 rounded-lg bg-blue-50 text-[#01257D] font-bold font-mono text-sm border border-blue-200 shadow-xs">
                ${result.ticker}
              </span>
              <h3 className="text-base font-bold text-slate-900">Financial Research Dossier</h3>
              {result.is_sample && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border border-amber-300 bg-amber-50 text-amber-800 shadow-xs">
                  Sample data
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopySummary}
                title="Copy bulleted executive memo to clipboard"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-[#01257D] border border-blue-200 text-xs font-semibold transition cursor-pointer"
              >
                {summaryCopied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <ClipboardList className="h-3.5 w-3.5 text-[#01257D]" />}
                <span>{summaryCopied ? 'Briefing Copied' : 'Executive Briefing'}</span>
              </button>

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
                title="Print or Save as PDF Dossier"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer shadow-xs"
              >
                <Printer className="h-3.5 w-3.5" />
                <span>Print</span>
              </button>
            </div>
          </div>

          {/* Report Body */}
          <div className="p-6 sm:p-8 space-y-6">
            {/* Bento Grid: Growth & Margin Scorecard + Key Indicators */}
            <div id="section-metrics" className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch scroll-mt-24">
              <div className="lg:col-span-5 flex flex-col">
                <GrowthMarginScorecard
                  metrics={result.metrics}
                  sentiment={result.sentiment}
                  ticker={result.ticker}
                  isSample={result.is_sample}
                />
              </div>
              <div className="lg:col-span-7 flex flex-col">
                <MetricsScorecard
                  metrics={result.metrics}
                  sentiment={result.sentiment}
                  ticker={result.ticker}
                />
              </div>
            </div>

            {/* Comprehensive Report */}
            <div id="section-report" className="scroll-mt-24">
              <MarkdownView content={result.report} />
            </div>

            {/* Interactive Dynamic Follow-Up Inquiry Chips */}
            <div id="section-inquiries" className="scroll-mt-24">
              <FollowUpQuestions
                ticker={result.ticker}
                onSelectQuestion={(q) => onNavigateCustom && onNavigateCustom(q)}
              />
            </div>

            {/* Source Citations Accordion */}
            {result.sources && result.sources.length > 0 && (
              <div id="section-sources" className="pt-4 border-t border-slate-200 scroll-mt-24">
                <button
                  type="button"
                  onClick={() => setShowSources(!showSources)}
                  className="flex items-center justify-between w-full text-xs font-semibold text-slate-700 hover:text-slate-900 transition cursor-pointer p-3 rounded-xl bg-slate-50 border border-slate-200 shadow-xs"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-[#01257D]" />
                    <span>Document Context Passages &amp; Evidence ({result.sources.length} Chunks)</span>
                  </span>
                  {showSources ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>

                {showSources && (
                  <div className="mt-3 space-y-2.5">
                    {result.sources.map((src, i) => (
                      <div
                        key={i}
                        className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/90 text-xs text-slate-700 space-y-1.5 shadow-xs"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-slate-600">
                          <span className="font-bold text-[#01257D]">
                            Citation [{i + 1}] &bull; {src.ticker || src.metadata?.ticker || result.ticker} &bull; {src.section || src.metadata?.section || 'Item 1'} ({src.form || '10-K'} FY{src.fiscal_year || src.metadata?.fiscal_year || ''})
                          </span>
                          <div className="flex items-center gap-2">
                            {src.rerank_score != null && (
                              <span className="bg-indigo-50 text-indigo-800 px-2 py-0.5 rounded border border-indigo-200 font-bold">
                                Rerank score: {src.rerank_score.toFixed(3)}
                              </span>
                            )}
                            {src.retrieval_score != null && (
                              <span className="bg-blue-50 text-[#01257D] px-2 py-0.5 rounded border border-blue-200 font-bold">
                                Retrieval score: {src.retrieval_score.toFixed(4)}
                              </span>
                            )}
                          </div>
                        </div>
                        {src.accession_number && (
                          <div className="text-[10px] text-slate-500 font-mono">
                            Accession: {src.accession_number}
                          </div>
                        )}
                        <p className="font-mono text-[11px] leading-relaxed text-slate-800 bg-white p-2.5 rounded-lg border border-slate-200/60">
                          {src.quote || src.text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Disclaimer at bottom of report */}
            <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-500 text-center">
              ApexEquity is for informational and educational research purposes only and does not constitute financial, legal, or investment advice.
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
