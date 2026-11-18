import React from 'react';
import { Award, TrendingUp, ShieldCheck, HelpCircle } from 'lucide-react';
import InfoTooltip from './InfoTooltip';

export default function GrowthMarginScorecard({ metrics, sentiment, ticker, isSample = false }) {
  const growth = metrics?.growth_yoy;
  const margin = metrics?.gross_margin;
  const revenue = metrics?.revenue_label || (metrics?.revenue ? `$${metrics.revenue}B` : null);
  const primaryDriver = metrics?.primary_driver;

  const defaultSource = isSample
    ? 'Illustrative sample, not from a document'
    : (metrics?.source || 'Hand-written summary');

  const defaultPeriod = isSample
    ? 'Illustrative sample, not from a document'
    : 'period not stated';

  const growthSource = metrics?.growth_source || defaultSource;
  const growthPeriod = metrics?.growth_period || defaultPeriod;

  const marginSource = metrics?.margin_source || defaultSource;
  const marginPeriod = metrics?.margin_period || defaultPeriod;

  const revSource = metrics?.revenue_source || defaultSource;
  const revPeriod = metrics?.revenue_period || defaultPeriod;

  const growthAccession = metrics?.growth_accession || metrics?.accession_number;
  const marginAccession = metrics?.margin_accession || metrics?.accession_number;
  const revAccession = metrics?.revenue_accession || metrics?.accession_number;

  const isSec = metrics?.source === 'SEC filing' || metrics?.source_badge?.includes('SEC') || metrics?.source?.toLowerCase().includes('sec');
  const hasData = (growth !== null && growth !== undefined) || (margin !== null && margin !== undefined);

  const badgeLabel = !hasData
    ? 'Data Absent'
    : isSample
    ? 'Sample data'
    : isSec
    ? 'SEC filing (XBRL)'
    : 'Ingested document';

  // Transparent, disclosed formula description
  const formulaExplanation =
    "Evaluation criteria: YoY Revenue Growth (>15% benchmark) paired with Gross Margin (>50% pricing power). Only computed when ingested documents or market filings disclose both figures.";

  // Factual headline derived purely from displayed figures, without ungrounded trend claims
  const headline = (() => {
    if (!hasData) return 'Not disclosed in the retrieved filings';
    const parts = [];
    if (growth !== null && growth !== undefined) {
      parts.push(`Revenue growth ${growth > 0 ? `+${growth}%` : `${growth}%`} YoY`);
    }
    if (margin !== null && margin !== undefined) {
      parts.push(`gross margin ${margin}%`);
    }
    if (parts.length === 0 && revenue) {
      parts.push(`revenue ${revenue}`);
    }
    return parts.length > 0 ? parts.join(', ') : 'Disclosed document financials';
  })();

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
            {badgeLabel}
          </span>
        </div>
      </div>

      {/* Center: Disclosed Inputs & Formula */}
      <div className="my-auto space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-extrabold text-slate-900 flex items-center gap-1.5">
              <span>${ticker} Document Extraction</span>
              {hasData && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              {headline}
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
        <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-center shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-center gap-1 text-[10px] text-slate-600 font-semibold mb-0.5">
              <TrendingUp className="h-3 w-3 text-[#01257D]" />
              <span>YoY Growth</span>
            </div>
            <span className="text-xs font-mono font-bold text-slate-900">
              {growth !== null && growth !== undefined ? (growth > 0 ? `+${growth}%` : `${growth}%`) : 'N/A'}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 text-[9px] text-slate-500 font-mono mt-1.5 pt-1 border-t border-slate-200/60 text-left break-words">
            <span className="font-semibold text-slate-700 break-words">{growthSource}</span>
            <span className="break-words text-slate-600 font-medium">{growthPeriod}</span>
            {growthAccession && (
              <span className="text-[8px] text-slate-400 break-all font-normal">
                Accn: {growthAccession}
              </span>
            )}
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-center shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-center gap-1 text-[10px] text-slate-600 font-semibold mb-0.5">
              <ShieldCheck className="h-3 w-3 text-[#01257D]" />
              <span>Gross Margin</span>
            </div>
            <span className="text-xs font-mono font-bold text-slate-900">
              {margin !== null && margin !== undefined ? `${margin}%` : 'N/A'}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 text-[9px] text-slate-500 font-mono mt-1.5 pt-1 border-t border-slate-200/60 text-left break-words">
            <span className="font-semibold text-slate-700 break-words">{marginSource}</span>
            <span className="break-words text-slate-600 font-medium">{marginPeriod}</span>
            {marginAccession && (
              <span className="text-[8px] text-slate-400 break-all font-normal">
                Accn: {marginAccession}
              </span>
            )}
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200/90 p-2.5 rounded-xl text-center shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-center gap-1 text-[10px] text-slate-600 font-semibold mb-0.5">
              <Award className="h-3 w-3 text-[#01257D]" />
              <span>Total Rev</span>
            </div>
            <span className="text-xs font-mono font-bold text-slate-900 truncate block">
              {revenue || 'N/A'}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 text-[9px] text-slate-500 font-mono mt-1.5 pt-1 border-t border-slate-200/60 text-left break-words">
            <span className="font-semibold text-slate-700 break-words">{revSource}</span>
            <span className="break-words text-slate-600 font-medium">{revPeriod}</span>
            {revAccession && (
              <span className="text-[8px] text-slate-400 break-all font-normal">
                Accn: {revAccession}
              </span>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
