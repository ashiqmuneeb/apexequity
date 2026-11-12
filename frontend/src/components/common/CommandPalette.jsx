import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  TrendingUp,
  GitCompare,
  MessageSquareText,
  FolderKanban,
  Zap,
  Key,
  RefreshCw,
  X,
  ArrowRight,
  ShieldCheck,
  Building,
} from 'lucide-react';
import { TABS, DEFAULT_TICKERS } from '../../constants/stockTickers';

export default function CommandPalette({
  isOpen,
  onClose,
  onSelectTab,
  onSelectTicker,
  onLaunchDemo,
  onOpenKeyModal,
  onRebuildIndex,
  onOpenTour,
}) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Trigger open via custom event or props if supported
        }
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const ALL_ACTIONS = [
    // Ticker jump
    {
      id: 'ticker-nvda',
      title: 'Analyze NVIDIA Corporation ($NVDA)',
      category: 'Securities',
      icon: TrendingUp,
      action: () => {
        onSelectTab(TABS.SINGLE);
        onSelectTicker('NVDA');
        onClose();
      },
    },
    {
      id: 'ticker-googl',
      title: 'Analyze Alphabet Inc. ($GOOGL)',
      category: 'Securities',
      icon: TrendingUp,
      action: () => {
        onSelectTab(TABS.SINGLE);
        onSelectTicker('GOOGL');
        onClose();
      },
    },
    {
      id: 'ticker-msft',
      title: 'Analyze Microsoft Corporation ($MSFT)',
      category: 'Securities',
      icon: TrendingUp,
      action: () => {
        onSelectTab(TABS.SINGLE);
        onSelectTicker('MSFT');
        onClose();
      },
    },
    {
      id: 'ticker-aapl',
      title: 'Analyze Apple Inc. ($AAPL)',
      category: 'Securities',
      icon: TrendingUp,
      action: () => {
        onSelectTab(TABS.SINGLE);
        onSelectTicker('AAPL');
        onClose();
      },
    },
    // Instant Demo
    {
      id: 'instant-demo',
      title: 'Launch Full Interactive Demo ($NVDA)',
      category: 'Quick Launch',
      icon: Zap,
      accent: 'text-[#00FFFF]',
      action: () => {
        onSelectTab(TABS.SINGLE);
        onLaunchDemo();
        onClose();
      },
    },
    // Navigation
    {
      id: 'tab-single',
      title: 'Go to Equity Research Report',
      category: 'Navigation',
      icon: TrendingUp,
      action: () => {
        onSelectTab(TABS.SINGLE);
        onClose();
      },
    },
    {
      id: 'tab-compare',
      title: 'Go to Peer & Moat Benchmark',
      category: 'Navigation',
      icon: GitCompare,
      action: () => {
        onSelectTab(TABS.COMPARE);
        onClose();
      },
    },
    {
      id: 'tab-custom',
      title: 'Go to Market Intelligence Terminal',
      category: 'Navigation',
      icon: MessageSquareText,
      action: () => {
        onSelectTab(TABS.CUSTOM);
        onClose();
      },
    },
    {
      id: 'tab-articles',
      title: 'Go to SEC Disclosures & Library',
      category: 'Navigation',
      icon: FolderKanban,
      action: () => {
        onSelectTab(TABS.ARTICLES);
        onClose();
      },
    },
    // System Actions
    {
      id: 'action-key',
      title: 'Configure Groq API Key',
      category: 'System',
      icon: Key,
      action: () => {
        onOpenKeyModal();
        onClose();
      },
    },
    {
      id: 'action-sync',
      title: 'Re-index & Synchronize SEC Filings',
      category: 'System',
      icon: RefreshCw,
      action: () => {
        onRebuildIndex();
        onClose();
      },
    },
    {
      id: 'action-tour',
      title: '1-Minute Architecture Walkthrough Tour',
      category: 'System',
      icon: ShieldCheck,
      action: () => {
        onOpenTour();
        onClose();
      },
    },
  ];

  const filtered = ALL_ACTIONS.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
      } else if (query.trim()) {
        // If query is an unknown ticker, jump to single stock and set it!
        onSelectTab(TABS.SINGLE);
        onSelectTicker(query.trim().toUpperCase());
        onClose();
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-slate-900/50 backdrop-blur-md animate-fade-in command-palette-backdrop">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col">
        
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200 bg-slate-50">
          <Search className="h-4.5 w-4.5 text-[#01257D] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type any ticker ($NVDA, TSLA) or action..."
            className="flex-1 bg-transparent text-slate-900 placeholder-slate-400 text-sm font-semibold focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-200 transition cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Action List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.map((item, idx) => {
            const Icon = item.icon;
            const isSelected = idx === selectedIndex;
            return (
              <button
                key={item.id}
                type="button"
                onClick={item.action}
                onMouseEnter={() => setSelectedIndex(idx)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left transition cursor-pointer ${
                  isSelected
                    ? 'bg-[#01257D] text-white shadow-xs'
                    : 'text-slate-700 hover:bg-slate-100 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`p-1.5 rounded-lg border ${
                      isSelected
                        ? 'bg-white/20 border-white/40 text-white'
                        : 'bg-slate-100 border-slate-200 text-[#01257D]'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold">{item.title}</div>
                    <div className={`text-[10px] ${isSelected ? 'text-blue-100' : 'text-slate-500'}`}>{item.category}</div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  {isSelected && <ArrowRight className="h-3.5 w-3.5 text-white" />}
                </div>
              </button>
            );
          })}

          {filtered.length === 0 && (
            <div className="text-center py-8 text-xs text-slate-500">
              No matching actions. Press <strong className="text-[#01257D]">Enter</strong> to audit <strong className="text-slate-900 font-mono">${query.toUpperCase()}</strong> directly.
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <div className="flex items-center gap-2">
            <span>&uarr;&darr; Navigate</span>
            <span>&bull;</span>
            <span>&crarr; Select</span>
            <span>&bull;</span>
            <span>ESC Close</span>
          </div>
          <span className="text-[#01257D] font-bold">ApexEquity Command</span>
        </div>

      </div>
    </div>
  );
}

