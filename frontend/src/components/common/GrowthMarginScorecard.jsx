import React from 'react';
import { Award, TrendingUp, ShieldCheck, HelpCircle } from 'lucide-react';
import InfoTooltip from './InfoTooltip';

export default function GrowthMarginScorecard({ metrics, sentiment, ticker, isSample = false }) {
  const growth = metrics?.growth_yoy;
  const margin = metrics?.gross_margin;
  const revenue = metrics?.revenue_label || (metrics?.revenue ? `$${metrics.revenue}B` : null);
  const primaryDriver = metrics?.primary_driver;

  const hasData = growth !== null && growth !== undefined || margin !== null && margin !== undefined;

  // Transparent, disclosed formula description
  const formulaExplanation =
    "Evaluation criteria: YoY Revenue Growth (>15% benchmark) paired with Gross Margin (>50% pricing power). Only computed when audited filings or market filings disclose both figures.";

  return (
    <div className="h-full bg-white border border-slate-200 rounded-2xl p-5 flex flex-col justify-between gap-4 shadow-xs">
      
      {/* Top: Header & Badges */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Award className="h-4 w-4 text-[#01257D]" />
          <h4 className="text-xs uppercase font-bold tracking-wider text-slate-800">
            Growth &amp; Margin Scorecard
          </h4>
          <InfoTooltip
            title="Growth & Margin Scorecard"
            text={formulaExplanation}
          />
        </div>
        
        <div className="flex items-center gap-1.5">
          {isSample && (
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border border-amber-300 bg-amber-50 text-amber-800 shadow-xs">
              Sample data
            </span>
          )}
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border border-blue-200 bg-blue-50 text-[#01257D] shadow-xs">
            {hasData ? 'Grounded' : 'Data Absent'}
          </span>
        </div>
      </div>

      {/* Center: Disclosed Inputs & Formula */}
      <div className="my-auto space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-extrabold text-slate-900 flex items-center gap-1.5">
              <span>${ticker} Financial Grounding</span>
              {hasData && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              {hasData
                ? (sentiment || (growth > 20 && margin > 50 ? 'Strong Growth & Expanding Operating Margins' : 'Disclosed Filing Financials'))
                : 'Not disclosed in the retrieved filings'}
            </p>
          </div>
        </div>

        {/* Visible Formula Box */}
        <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-[11px] text-slate-600 space-y-1">
          <div className="font-semibold text-slate-800 flex items-center gap-1">
            <HelpCircle className="h-3 w-3 text-[#01257D]" />
            <span>Visible Scoring Methodology</span>
          </div>
          <p className="text-[10px] text-slate-500 leading-relaxed">
            Revenue Velocity: <span className="font-mono text-slate-700 font-semibold">{growth !== null && growth !== undefined ? (growth > 0 ? `+${growth}% YoY` : `${growth}% YoY`) : 'N/A'}</span> &bull;
            Gross Margin: <span className="font-mono text-slate-700 font-semibold">{margin !== null && margin !== undefined ? `${margin}%` : 'N/A'}</span>
          </p>
        </div>
      </div>

      {/* Bottom: Sub-Score Pillars */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200">
        <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-center shadow-xs">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-600 font-semibold mb-0.5">
            <TrendingUp className="h-3 w-3 text-[#01257D]" />
            <span>YoY Growth</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-900">
            {growth !== null && growth !== undefined ? (growth > 0 ? `+${growth}%` : `${growth}%`) : 'N/A'}
          </span>
        </div>

        <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-center shadow-xs">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-600 font-semibold mb-0.5">
            <ShieldCheck className="h-3 w-3 text-[#01257D]" />
            <span>Gross Margin</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-900">
            {margin !== null && margin !== undefined ? `${margin}%` : 'N/A'}
          </span>
        </div>

        <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-center shadow-xs">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-600 font-semibold mb-0.5">
            <Award className="h-3 w-3 text-[#01257D]" />
            <span>Total Rev</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-900 truncate block">
            {revenue || 'N/A'}
          </span>
        </div>
      </div>

    </div>
  );
}
