import React from 'react';
import { DollarSign, Percent, Zap, ShieldCheck, Sparkles } from 'lucide-react';
import AnimatedCounter from './AnimatedCounter';
import MiniSparkline from './MiniSparkline';
import InfoTooltip from './InfoTooltip';

export default function MetricsScorecard({ metrics, sentiment, ticker }) {
  if (!metrics) return null;

  const isSample = metrics.source === 'Sample data';
  const hasData = metrics.revenue !== null || metrics.growth_yoy !== null || metrics.gross_margin !== null;
  const isSec = metrics.source === 'SEC filing' || metrics.source_badge?.includes('SEC') || metrics.source?.toLowerCase().includes('sec');

  const defaultSource = isSample
    ? 'Illustrative sample, not from a document'
    : (metrics.source || 'Hand-written summary');

  const defaultPeriod = isSample
    ? 'Illustrative sample, not from a document'
    : 'period not stated';

  const revSource = metrics.revenue_source || defaultSource;
  const revPeriod = metrics.revenue_period || defaultPeriod;
  const revAccession = metrics.revenue_accession || metrics.accession_number;

  const growthSource = metrics.growth_source || defaultSource;
  const growthPeriod = metrics.growth_period || defaultPeriod;
  const growthAccession = metrics.growth_accession || metrics.accession_number;

  const marginSource = metrics.margin_source || defaultSource;
  const marginPeriod = metrics.margin_period || defaultPeriod;
  const marginAccession = metrics.margin_accession || metrics.accession_number;

  const driverSource = metrics.driver_source || defaultSource;
  const driverPeriod = metrics.driver_period || defaultPeriod;
  const driverAccession = metrics.driver_accession || metrics.accession_number;

  const isDriverFromData = Boolean(
    metrics.primary_driver &&
    !metrics.primary_driver.startsWith('Form 10-K Audited Disclosures') &&
    !metrics.primary_driver.startsWith('Ingested Document')
  );

  const badgeText = isSample
    ? 'Sample data (old 2023-24)'
    : !hasData
    ? 'Data Absent'
    : isSec
    ? 'SEC filing (XBRL)'
    : 'Ingested document';

  const sentimentColor =
    sentiment?.includes('Strong') || sentiment?.includes('Positive')
      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
      : sentiment?.includes('Moderate')
      ? 'bg-blue-50 text-[#01257D] border-blue-200'
      : sentiment?.includes('Neutral')
      ? 'bg-slate-100 text-slate-800 border-slate-200'
      : 'bg-amber-50 text-amber-800 border-amber-200';

  return (
    <div className="h-full bg-white border border-slate-200 rounded-2xl p-5 flex flex-col justify-between shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-800">
            Key Financial Indicators
          </span>
          {isSample ? (
            <span className="text-[10px] bg-amber-50 text-amber-800 border border-amber-300 px-2 py-0.5 rounded font-mono font-bold shadow-xs">
              Sample data (old 2023-24)
            </span>
          ) : (
            <span className="text-[10px] bg-blue-50 text-[#01257D] border border-blue-200 px-2 py-0.5 rounded font-mono font-bold shadow-xs">
              {badgeText}
            </span>
          )}
          {metrics.accession_number && (
            <span className="text-[10px] bg-slate-100 text-slate-700 border border-slate-300 px-2 py-0.5 rounded font-mono shadow-xs" title={`SEC Accession Number: ${metrics.accession_number}`}>
              Accn: {metrics.accession_number}
            </span>
          )}
          <InfoTooltip
            title="Ingested Disclosures"
            text="Financial metrics extracted directly from ingested documents or market snapshot without algorithmic extrapolation."
          />
        </div>

        {sentiment && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-600 font-medium">Latest fiscal year (SEC):</span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border flex items-center gap-1.5 ${sentimentColor}`}
            >
              <Sparkles className="h-3 w-3 text-[#01257D]" />
              <span>{sentiment}</span>
            </span>
          </div>
        )}
      </div>

      <div className={`grid gap-3 my-auto ${isDriverFromData ? 'grid-cols-2 md:grid-cols-4' : 'grid-cols-1 sm:grid-cols-3'}`}>
        {/* Metric 1: Revenue */}
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3.5 hover:border-blue-300 hover:bg-blue-50/20 transition flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
              <div className="flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5 text-[#01257D]" />
                <span className="font-medium">Total Revenue</span>
              </div>
              <InfoTooltip
                title="Revenue"
                text="Total revenue recognized for the reported period."
              />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <div className="text-xl font-bold font-mono text-slate-900">
                <AnimatedCounter value={metrics.revenue_label || (metrics.revenue ? `$${metrics.revenue}B` : 'N/A')} />
              </div>
              <MiniSparkline trend="up" width={42} height={16} />
            </div>
          </div>
          <div className="flex flex-col gap-0.5 text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60 text-left break-words">
            <span className="font-semibold text-slate-700 break-words">{revSource}</span>
            <span className="break-words text-slate-600 font-medium">{revPeriod}</span>
            {revAccession && (
              <span className="text-[9px] text-slate-400 break-all font-normal">
                Accn: {revAccession}
              </span>
            )}
          </div>
        </div>

        {/* Metric 2: Growth YoY */}
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3.5 hover:border-blue-300 hover:bg-blue-50/20 transition flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
              <div className="flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-[#01257D]" />
                <span className="font-medium">YoY Growth</span>
              </div>
              <InfoTooltip
                title="Year-over-Year Growth"
                text="Reported revenue growth relative to the comparable prior-year period."
              />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <div className="text-xl font-bold font-mono text-[#01257D]">
                <AnimatedCounter value={metrics.growth_label || (metrics.growth_yoy !== null && metrics.growth_yoy !== undefined ? (metrics.growth_yoy > 0 ? `+${metrics.growth_yoy}%` : `${metrics.growth_yoy}%`) : 'N/A')} />
              </div>
              <MiniSparkline trend={metrics.growth_yoy < 0 ? "down" : "up"} width={42} height={16} />
            </div>
          </div>
          <div className="flex flex-col gap-0.5 text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60 text-left break-words">
            <span className="font-semibold text-slate-700 break-words">{growthSource}</span>
            <span className="break-words text-slate-600 font-medium">{growthPeriod}</span>
            {growthAccession && (
              <span className="text-[9px] text-slate-400 break-all font-normal">
                Accn: {growthAccession}
              </span>
            )}
          </div>
        </div>

        {/* Metric 3: Gross Margin */}
        <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3.5 hover:border-blue-300 hover:bg-blue-50/20 transition flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
              <div className="flex items-center gap-1.5">
                <Percent className="h-3.5 w-3.5 text-[#01257D]" />
                <span className="font-medium">Gross Margin</span>
              </div>
              <InfoTooltip
                title="Gross Margin"
                text="Gross profit margin percentage as disclosed in the filings."
              />
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <div className="text-xl font-bold font-mono text-[#01257D]">
                <AnimatedCounter value={metrics.margin_label || (metrics.gross_margin !== null && metrics.gross_margin !== undefined ? `${metrics.gross_margin}%` : 'N/A')} />
              </div>
              <MiniSparkline trend="up" width={42} height={16} />
            </div>
          </div>
          <div className="flex flex-col gap-0.5 text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60 text-left break-words">
            <span className="font-semibold text-slate-700 break-words">{marginSource}</span>
            <span className="break-words text-slate-600 font-medium">{marginPeriod}</span>
            {marginAccession && (
              <span className="text-[9px] text-slate-400 break-all font-normal">
                Accn: {marginAccession}
              </span>
            )}
          </div>
        </div>

        {/* Metric 4: Primary Driver (Only rendered when derived from actual data) */}
        {isDriverFromData && (
          <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-3.5 hover:border-blue-300 hover:bg-blue-50/20 transition flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-[#01257D]" />
                  <span className="font-medium">Core Driver</span>
                </div>
                <InfoTooltip
                  title="Primary Segment"
                  text="Primary industry segment or technological catalyst contributing to operating revenue."
                />
              </div>
              <div className="text-sm font-bold text-slate-900 mt-1 break-words leading-snug" title={metrics.primary_driver}>
                {metrics.primary_driver}
              </div>
            </div>
            <div className="flex flex-col gap-0.5 text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60 text-left break-words">
              <span className="font-semibold text-slate-700 break-words">{driverSource}</span>
              <span className="break-words text-slate-600 font-medium">{driverPeriod}</span>
              {driverAccession && (
                <span className="text-[9px] text-slate-400 break-all font-normal">
                  Accn: {driverAccession}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="text-right text-[10px] text-slate-500 font-mono mt-3">
        Extracted Financial Metrics &bull; Ingested Document Snapshot
      </div>
    </div>
  );
}
