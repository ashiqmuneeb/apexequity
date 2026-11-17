import React from 'react';
import { TrendingUp, GitCompare, MessageSquareText, FolderKanban } from 'lucide-react';
import { TABS } from '../../constants/stockTickers';

export default function TabNavigation({ activeTab, onTabChange, articleCount = 0 }) {
  const tabs = [
    {
      id: TABS.SINGLE,
      label: 'Stock Analysis',
      icon: TrendingUp,
    },
    {
      id: TABS.COMPARE,
      label: 'Compare Stocks',
      icon: GitCompare,
    },
    {
      id: TABS.CUSTOM,
      label: 'Ask AI',
      icon: MessageSquareText,
    },
    {
      id: TABS.ARTICLES,
      label: 'SEC Filings',
      badge: articleCount ?? 0,
      icon: FolderKanban,
    },
  ];

  return (
    <div className="w-full flex items-center justify-start pb-1 overflow-x-auto scrollbar-none">
      <div className="bg-slate-200/70 border border-slate-300/80 p-1.5 rounded-xl backdrop-blur-md inline-flex items-center gap-1.5 shadow-xs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg transition cursor-pointer whitespace-nowrap ${
                isActive
                  ? 'bg-white text-[#01257D] shadow-xs border border-slate-200/80 font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-[#01257D]' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`text-[11px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                    isActive
                      ? 'bg-blue-100 text-[#01257D]'
                      : 'bg-slate-300 text-slate-700'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
