import React from 'react';
import { DollarSign, Percent, Zap, ShieldCheck, Sparkles } from 'lucide-react';
import AnimatedCounter from './AnimatedCounter';
import MiniSparkline from './MiniSparkline';
import InfoTooltip from './InfoTooltip';

export default function MetricsScorecard({ metrics, sentiment, ticker }) {
  if (!metrics) return null;

  const isSample = metrics.source === 'Sample data';
  const hasData = metrics.revenue !== null || metrics.growth_yoy !== null || metrics.gross_margin !== null;

  const defaultSource = isSample
    ? 'Yahoo Finance snapshot'
    : (metrics.source === 'SEC filing' ? 'SEC filing' : 'Yahoo Finance snapshot');

  const revSource = metrics.revenue_source || defaultSource;
  const revPeriod = metrics.revenue_period || 'period not stated';

  const growthSource = metrics.growth_source || defaultSource;
  const growthPeriod = metrics.growth_period || 'period not stated';

  const marginSource = metrics.margin_source || defaultSource;
  const marginPeriod = metrics.margin_period || 'period not stated';

  const driverSource = metrics.driver_source || defaultSource;
  const driverPeriod = metrics.driver_period || 'period not stated';

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
              Sample data
            </span>
          ) : (
            <span className="text-[10px] bg-blue-50 text-[#01257D] border border-blue-200 px-2 py-0.5 rounded font-mono font-bold shadow-xs">
              {metrics.source_badge || (metrics.source ? `From ${metrics.source}` : 'From ingested document')}
            </span>
          )}
          <InfoTooltip
            title="Ingested Disclosures"
            text="Financial metrics extracted directly from ingested documents or market snapshot without algorithmic extrapolation."
          />
        </div>

        {sentiment && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-600 font-medium">Outlook:</span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border flex items-center gap-1.5 ${sentimentColor}`}
            >
              <Sparkles className="h-3 w-3 text-[#01257D]" />
              <span>{sentiment}</span>
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-auto">
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
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60">
            <span>{revSource}</span>
            <span>{revPeriod}</span>
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
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60">
            <span>{growthSource}</span>
            <span>{growthPeriod}</span>
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
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60">
            <span>{marginSource}</span>
            <span>{marginPeriod}</span>
          </div>
        </div>

        {/* Metric 4: Primary Driver */}
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
            <div className="text-sm font-bold text-slate-900 truncate mt-1" title={metrics.primary_driver || 'Disclosed in Filing'}>
              {metrics.primary_driver || (hasData ? 'Disclosed in Filing' : 'N/A')}
            </div>
          </div>
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mt-2 pt-1.5 border-t border-slate-200/60">
            <span>{driverSource}</span>
            <span>{driverPeriod}</span>
          </div>
        </div>
      </div>

      <div className="text-right text-[10px] text-slate-500 font-mono mt-3">
        Extracted Financial Metrics &bull; Ingested Document Snapshot
      </div>
    </div>
  );
}
