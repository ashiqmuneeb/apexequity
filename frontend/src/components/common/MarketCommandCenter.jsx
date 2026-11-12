import React from 'react';
import { ArrowUpRight, Zap, ShieldCheck } from 'lucide-react';
import AnimatedCounter from './AnimatedCounter';
import MiniSparkline from './MiniSparkline';

const COVERAGE_COMPANIES = [
  {
    ticker: 'NVDA',
    name: 'NVIDIA Corporation',
    sector: 'AI Compute & Silicon',
    revenue: '$22.10B',
    growth: '+265% YoY',
    margin: '76.0%',
    trend: 'up',
  },
  {
    ticker: 'MSFT',
    name: 'Microsoft Corporation',
    sector: 'Cloud & AI Copilot',
    revenue: '$62.00B',
    growth: '+18% YoY',
    margin: '68.0%',
    trend: 'up',
  },
  {
    ticker: 'GOOGL',
    name: 'Alphabet Inc.',
    sector: 'Search & Cloud Platform',
    revenue: '$86.30B',
    growth: '+13% YoY',
    margin: '56.5%',
    trend: 'up',
  },
  {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    sector: 'Hardware & Services',
    revenue: '$119.60B',
    growth: '+2% YoY',
    margin: '45.9%',
    trend: 'down',
  },
];

export default function MarketCommandCenter({ onSelectStock, onQuickAnalyze, onLaunchDemo }) {
  return (
    <div className="space-y-4 animate-fade-in">
      
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            Coverage Universe
          </h3>
          <p className="text-xs text-slate-600">
            Select a security to synthesize audited Form 10-K balance sheet and risk disclosures.
          </p>
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

      {/* Clean 4-Card Grid on Matte White */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {COVERAGE_COMPANIES.map((company) => (
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
                <span className="text-[10px] text-slate-600 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  10-K Filed
                </span>
              </div>

              {/* Company Info */}
              <h4 className="text-sm font-bold text-slate-900 group-hover:text-[#01257D] transition">
                {company.name}
              </h4>
              <p className="text-xs text-slate-500 mb-3.5">{company.sector}</p>

              {/* Financial Snapshot Pod */}
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200/80 space-y-2.5 mb-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">Audited Rev</span>
                  <span className="font-mono font-bold text-slate-900">
                    <AnimatedCounter value={company.revenue} />
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">YoY Growth</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-emerald-600">
                      <AnimatedCounter value={company.growth} />
                    </span>
                    <MiniSparkline trend={company.trend} width={34} height={14} />
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-600 font-medium">Gross Margin</span>
                  <span className="font-mono font-bold text-slate-800">
                    <AnimatedCounter value={company.margin} />
                  </span>
                </div>
              </div>
            </div>

            {/* Action */}
            <button
              type="button"
              onClick={() => onQuickAnalyze(company.ticker)}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-[#01257D] hover:bg-[#0244c9] text-white text-xs font-semibold transition cursor-pointer shadow-xs"
            >
              <span>Analyze ${company.ticker}</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Grounding Note */}
      <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-200">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-[#01257D]" />
          <span>Ground-truth RAG from Form 10-K filings &bull; Zero Hallucination Design</span>
        </div>
        <span className="text-slate-500 font-mono text-[11px]">Groq LPU Acceleration</span>
      </div>

    </div>
  );
}
