import React from 'react';
import { TrendingUp, RefreshCw, GraduationCap, Search } from 'lucide-react';

export default function Header({
  status,
  onOpenKeyModal,
  onRebuildIndex,
  isRebuilding,
  onOpenTour,
  onOpenCommandPalette,
}) {
  return (
    <header className="border-b border-slate-200/80 bg-white/85 backdrop-blur-xl sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Left: Clean Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-[#01257D] via-[#0244c9] to-[#00b4d8] flex items-center justify-center shadow-md shadow-[#01257D]/15 ring-1 ring-[#00b4d8]/40">
            <TrendingUp className="h-4.5 w-4.5 text-white stroke-[2.5]" />
          </div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-[#01257D] flex items-center">
              <span>Apex</span><span className="text-[#00A3C4]">Equity</span>
            </h1>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-[#01257D] border border-blue-200 px-2.5 py-0.5 rounded-full hidden sm:inline-block shadow-xs">
              Filing Analysis RAG
            </span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2.5 shrink-0">
          
          {/* Quick Search Ctrl+K Button */}
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="flex items-center gap-2 h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 hover:border-[#01257D]/40 text-xs font-medium transition cursor-pointer shadow-xs"
            title="Press Ctrl+K to search (or Cmd+K)"
          >
            <Search className="h-3.5 w-3.5 text-[#01257D]" />
            <span className="hidden sm:inline text-slate-600 text-xs">Search</span>
            <kbd className="hidden sm:inline text-[9px] bg-white text-slate-600 border border-slate-200 rounded px-1.5 py-0.5 font-mono shadow-xs">
              Ctrl K
            </kbd>
          </button>
          
          {/* Starter Tour */}
          <button
            type="button"
            onClick={onOpenTour}
            className="h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer flex items-center gap-1.5 shadow-xs"
            title="How this application works in 30 seconds"
          >
            <GraduationCap className="h-3.5 w-3.5 text-[#01257D]" />
            <span className="hidden sm:inline">Tour</span>
          </button>

          {/* Sync Database */}
          <button
            type="button"
            onClick={onRebuildIndex}
            disabled={isRebuilding}
            title="Re-index financial filings vector database"
            className="h-9 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-[#01257D] ${isRebuilding ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isRebuilding ? 'Syncing...' : 'Sync'}</span>
          </button>

          {/* API Key Status */}
          <button
            type="button"
            onClick={onOpenKeyModal}
            className={`h-9 px-3 rounded-xl text-xs font-semibold border transition cursor-pointer flex items-center gap-2 shadow-xs ${
              status?.has_groq_key
                ? 'bg-blue-50/80 hover:bg-blue-100/80 text-[#01257D] border-blue-200'
                : 'bg-amber-50 hover:bg-amber-100 text-amber-800 border-amber-300 animate-pulse'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                status?.has_groq_key ? 'bg-emerald-500 shadow-sm shadow-emerald-400' : 'bg-amber-500'
              }`}
            />
            <span className="hidden sm:inline">
              {status?.has_groq_key ? 'API Ready' : 'Configure API Key'}
            </span>
          </button>

        </div>
      </div>
    </header>
  );
}
