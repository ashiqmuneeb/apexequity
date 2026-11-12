import React, { useState, useEffect } from 'react';
import { Sparkles, Copy, Check, Download, ChevronDown, ChevronUp, FileText, Printer, ClipboardList, Zap, ArrowUp } from 'lucide-react';
import { analysisApi } from '../../api/analysisApi';
import MarkdownView from '../../components/common/MarkdownView';
import LoadingSkeleton from '../../components/common/LoadingSkeleton';
import ErrorCard from '../../components/common/ErrorCard';
import MetricsScorecard from '../../components/common/MetricsScorecard';
import FinancialHealthGauge from '../../components/common/FinancialHealthGauge';
import FollowUpQuestions from '../../components/common/FollowUpQuestions';
import InfoTooltip from '../../components/common/InfoTooltip';
import MarketCommandCenter from '../../components/common/MarketCommandCenter';
import { DEFAULT_TICKERS } from '../../constants/stockTickers';
import { DEMO_SINGLE_STOCK } from '../../constants/demoData';

export default function SingleStockView({ availableTickers = [], onOpenKeyModal, onNavigateCustom }) {
  const [ticker, setTicker] = useState('NVDA');
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

  const handleLoadDemo = () => {
    setTicker('NVDA');
    setResult(DEMO_SINGLE_STOCK);
    setError(null);
  };

  const handleCopy = () => {
    if (!result?.report) return;
    navigator.clipboard.writeText(result.report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopySummary = () => {
    if (!result) return;
    const summaryText = `ApexEquity Research Briefing: $${result.ticker}\n` +
      `• Reported Revenue: ${result.metrics?.revenue_label || '$' + result.metrics?.revenue + 'B' || 'N/A'}\n` +
      `• YoY Growth: ${result.metrics?.growth_label || '+' + result.metrics?.growth_yoy + '%' || 'N/A'}\n` +
      `• Gross Margin: ${result.metrics?.margin_label || result.metrics?.gross_margin + '%' || 'N/A'}\n` +
      `• Core Growth Engine: ${result.metrics?.primary_driver || 'N/A'}\n` +
      `• Investment Outlook: ${result.sentiment || 'N/A'}`;
    navigator.clipboard.writeText(summaryText);
    setSummaryCopied(true);
    setTimeout(() => setSummaryCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!result?.report) return;
    const blob = new Blob([result.report], { type: 'text/markdown' });
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
      <div className="terminal-card bg-white border border-slate-200 rounded-xl p-5.5 shadow-xs relative overflow-hidden backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span>Financial Equity Research</span>
              <span className="text-[11px] font-bold text-[#01257D] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200 shadow-xs">
                SEC 10-K Grounded
              </span>
            </h2>
            <p className="text-xs text-slate-600 mt-1">
              Instant equity research memo synthesizing audited revenue, operating margins, and risk disclosures.
            </p>
          </div>

          {/* Quick Select Chips */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-slate-500 mr-1 font-medium">Quick Select:</span>
            {quickTickers.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTicker(t)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider transition cursor-pointer ${
                  ticker.toUpperCase() === t
                    ? 'bg-[#01257D] text-white border border-[#01257D] shadow-xs'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200'
                }`}
              >
                ${t}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleGenerate} className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-2.5 items-center">
            <div className="relative flex-1 w-full">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 font-mono text-sm font-semibold">
                $
              </div>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Enter Ticker (e.g. NVDA, AAPL, MSFT, GOOGL)"
                className="w-full h-11 pl-8 pr-4 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 text-sm font-semibold tracking-wide focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !ticker.trim()}
              className="w-full sm:w-auto h-11 px-6 bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] hover:opacity-95 text-white font-bold text-sm rounded-xl shadow-md transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2 whitespace-nowrap"
            >
              {loading ? (
                <>
                  <div className="h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Auditing SEC Filings...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-cyan-200" />
                  <span>Analyze Stock</span>
                </>
              )}
            </button>
          </div>

          {/* Toggle Custom Prompt */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setCustomPromptEnabled(!customPromptEnabled)}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 cursor-pointer font-medium"
            >
              <span>{customPromptEnabled ? '− Standard Research Framework' : '+ Tailor Investment Thesis & Scope'}</span>
            </button>

            {customPromptEnabled && (
              <div className="mt-2.5">
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder={`Framework: Generate an institutional financial analysis dossier for ticker ${ticker || 'NVDA'}. Highlight revenue momentum, margin trajectory, cloud/AI infrastructure investments, and primary regulatory risk factors.`}
                  rows={3}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D]"
                />
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Error Card */}
      <ErrorCard
        title="Analysis Error"
        message={error}
        onConfigureKey={onOpenKeyModal}
      />

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

      {/* Floating Sticky Header Capsule on Scroll */}
      {result && isScrolled && (
        <div className="fixed top-18 left-1/2 -translate-x-1/2 z-30 max-w-4xl w-[92%] bg-white/95 border border-slate-300 rounded-full py-2 px-5 backdrop-blur-xl shadow-xl flex items-center justify-between gap-4 animate-fade-in ring-1 ring-slate-200">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-[#01257D] font-mono font-bold text-xs border border-blue-200 shadow-xs">
              ${result.ticker}
            </span>
            <span className="text-xs text-slate-800 font-semibold hidden sm:inline">
              {result.metrics?.revenue_label || (result.metrics?.revenue ? `$${result.metrics?.revenue}B` : '')}
            </span>
            <span className="text-xs text-[#01257D] font-mono font-bold hidden md:inline">
              {result.metrics?.growth_label || (result.metrics?.growth_yoy ? `+${result.metrics?.growth_yoy}% YoY` : '')}
            </span>
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
              <h3 className="text-base font-bold text-slate-900">Financial Deep-Dive Outlook</h3>
            </div>

            <div className="flex items-center gap-2">
              {/* Executive Summary Button */}
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
                <span className="hidden sm:inline">Print PDF</span>
              </button>
            </div>
          </div>

          {/* Report Body */}
          <div className="p-6 sm:p-8 space-y-6">
            {/* Bento Grid: Health Quotient & Key Financial Indicators */}
            <div id="section-metrics" className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch scroll-mt-24">
              <div className="lg:col-span-5 flex flex-col">
                <FinancialHealthGauge
                  metrics={result.metrics}
                  sentiment={result.sentiment}
                  ticker={result.ticker}
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
                onSelectQuestion={onNavigateCustom}
              />
            </div>
          </div>

          {/* Sources Section */}
          {result.sources && result.sources.length > 0 && (
            <div id="section-sources" className="border-t border-slate-200 bg-slate-50/80 p-6 scroll-mt-24">
              <button
                type="button"
                onClick={() => setShowSources(!showSources)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-700 hover:text-[#01257D] transition cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-[#01257D]" />
                  <span>Audited SEC Filings & Citation Excerpts ({result.sources.length} Disclosures Cited)</span>
                  <InfoTooltip
                    title="Audit Traceability"
                    text="Excerpts retrieved directly from local Form 10-K/10-Q filing documents using vector cosine similarity."
                  />
                </div>
                {showSources ? <ChevronUp className="h-4 w-4 text-[#01257D]" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showSources && (
                <div className="mt-4 space-y-3">
                  {result.sources.map((src, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs space-y-1.5 shadow-xs">
                      <div className="flex items-center justify-between text-slate-500">
                        <span className="font-mono text-[#01257D] font-bold">Disclosure Citation #{i + 1}</span>
                        {src.score && (
                          <span className="text-[11px] text-[#01257D] font-mono bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-bold">
                            Audit Confidence: {(src.score * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                      <p className="text-slate-700 leading-relaxed font-mono text-[11px] bg-slate-50 p-3 rounded-lg border border-slate-200">
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
