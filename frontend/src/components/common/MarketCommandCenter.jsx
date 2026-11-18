import React, { useState, useEffect } from 'react';
import { ArrowUpRight, Zap, Folder, ShieldCheck } from 'lucide-react';
import { demoApi } from '../../api/demoApi';
import { articlesApi } from '../../api/articlesApi';

export default function MarketCommandCenter({ onSelectStock, onQuickAnalyze, onLaunchDemo }) {
  const [companies, setCompanies] = useState([]);
  const [isSample, setIsSample] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const loadCoverage = async () => {
      try {
        // Fetch sample coverage universe from backend demo endpoint
        const demoData = await demoApi.getDemo('coverage');
        if (mounted && demoData?.companies) {
          setCompanies(demoData.companies);
          setIsSample(true);
        }
      } catch (err) {
        // Fallback: derive from real articles list
        try {
          const articlesData = await articlesApi.listArticles();
          if (mounted && articlesData?.articles) {
            setCompanies(
              articlesData.articles.map((a) => ({
                ticker: a.ticker,
                name: `${a.ticker} Corporation`,
                sector: 'Ingested Security',
                revenue: 'Disclosed in Filing',
                growth: 'Disclosed in Filing',
                margin: 'Disclosed in Filing',
                badge: 'Ingested',
              }))
            );
            setIsSample(false);
          }
        } catch {
          // ignore
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadCoverage();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-4 animate-fade-in">
      
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2">
        <div className="flex items-center gap-2">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>Coverage Universe</span>
              {isSample && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border border-amber-300 bg-amber-50 text-amber-800 shadow-xs">
                  Sample data
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-600">
              Select a security to synthesize ingested disclosures, balance sheets, and risk factors.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onLaunchDemo}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-[#01257D] border border-blue-200 text-xs font-semibold transition cursor-pointer shadow-xs"
        >
          <Zap className="h-3.5 w-3.5 text-[#01257D]" />
          <span>Try Instant Demo ($NVDA)</span>
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {companies.map((company) => (
          <div
            key={company.ticker}
            className="terminal-card bg-white border border-slate-200 hover:border-[#01257D]/50 hover:shadow-lg rounded-xl p-5 transition flex flex-col justify-between group shadow-xs"
          >
            <div>
              {/* Header */}
              <div className="flex items-center justify-between mb-2">
                <span className="px-2.5 py-0.5 rounded-md bg-blue-50 text-[#01257D] font-mono font-bold text-xs border border-blue-200 shadow-xs">
                  ${company.ticker}
                </span>
                <span className="text-[10px] text-amber-800 font-mono bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  {company.badge || 'Sample Data'}
                </span>
              </div>

              {/* Company Info */}
              <h4 className="text-sm font-bold text-slate-900 group-hover:text-[#01257D] transition">
                {company.name}
              </h4>
              <p className="text-xs text-slate-500 mb-3.5">{company.sector}</p>

              {/* Financial Snapshot Pod */}
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200/80 space-y-2 mb-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">Revenue</span>
                  <span className="font-mono font-bold text-slate-900">
                    {company.revenue}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">YoY Velocity</span>
                  <span className="font-mono font-bold text-[#01257D]">
                    {company.growth}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">Gross Margin</span>
                  <span className="font-mono font-bold text-slate-900">
                    {company.margin}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1.5 border-t border-slate-200/60">
                  <span>{company.source || 'Illustrative sample, not from a document'}</span>
                  <span>{company.period || 'period not stated'}</span>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => onSelectStock(company.ticker)}
                className="flex-1 py-1.5 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition cursor-pointer text-center"
              >
                Select
              </button>
              <button
                type="button"
                onClick={() => onQuickAnalyze(company.ticker)}
                className="flex items-center justify-center gap-1 py-1.5 px-3 rounded-lg bg-[#01257D] hover:bg-[#023b9c] text-white text-xs font-bold transition cursor-pointer shadow-xs"
              >
                <span>Analyze</span>
                <ArrowUpRight className="h-3 w-3" />
              </button>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
