import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const MARKET_DATA = [
  { symbol: 'NVDA', price: '$138.25', change: '+3.42%', up: true },
  { symbol: 'GOOGL', price: '$182.10', change: '+1.18%', up: true },
  { symbol: 'MSFT', price: '$442.80', change: '+0.85%', up: true },
  { symbol: 'AAPL', price: '$228.50', change: '-0.38%', up: false },
  { symbol: 'S&P 500', price: '5,864.67', change: '+0.45%', up: true },
  { symbol: 'NASDAQ', price: '18,518.61', change: '+0.62%', up: true },
];

export default function TickerTape({ onSelectTicker }) {
  return (
    <div className="bg-slate-100/90 border-b border-slate-200 py-1.5 text-xs font-mono select-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-6 overflow-x-auto scrollbar-none">
        <div className="flex items-center gap-6">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider shrink-0">
            Market Tape:
          </span>

          <div className="flex items-center gap-6 shrink-0">
            {MARKET_DATA.map((item) => (
              <button
                key={item.symbol}
                type="button"
                onClick={() => onSelectTicker && onSelectTicker(item.symbol)}
                className="flex items-center gap-2 hover:opacity-80 transition cursor-pointer text-slate-700"
              >
                <span className="font-bold text-[#01257D]">${item.symbol}</span>
                <span className="text-slate-600">{item.price}</span>
                <span
                  className={`flex items-center gap-0.5 text-[11px] font-semibold ${
                    item.up ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {item.up ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
                  <span>{item.change}</span>
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="hidden lg:flex items-center gap-2 text-[11px] text-slate-600 font-sans shrink-0">
          <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-xs" />
          <span>SEC 10-K Live Corpus</span>
        </div>
      </div>
    </div>
  );
}
