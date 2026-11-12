import React from 'react';
import { AlertTriangle, Key, RefreshCw } from 'lucide-react';

export default function StatusBanner({ status, onOpenKeyModal, onRebuildIndex, isRebuilding }) {
  if (!status) return null;

  if (!status.has_groq_key) {
    return (
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 text-amber-900 shadow-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
            <span>
              <strong>Groq API Key Required:</strong> Add your free key to generate stock research reports using Llama 3.3 70B.
            </span>
          </div>
          <button
            onClick={onOpenKeyModal}
            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg text-xs transition cursor-pointer flex items-center gap-1.5 shadow-xs"
          >
            <Key className="h-3.5 w-3.5" />
            <span>Set Groq API Key</span>
          </button>
        </div>
      </div>
    );
  }

  if (!status.index_initialized) {
    return (
      <div className="bg-blue-50 border-b border-blue-200 px-4 py-3 text-[#01257D] shadow-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4 w-4 text-[#01257D] shrink-0" />
            <span>
              <strong className="text-[#01257D]">Vector Store Uninitialized:</strong> Create local embeddings from the articles directory to enable semantic search.
            </span>
          </div>
          <button
            onClick={onRebuildIndex}
            disabled={isRebuilding}
            className="px-3 py-1.5 bg-[#01257D] hover:bg-[#0244c9] text-white font-bold rounded-lg text-xs transition cursor-pointer flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRebuilding ? 'animate-spin' : ''}`} />
            <span>{isRebuilding ? 'Indexing...' : 'Build Vector Index'}</span>
          </button>
        </div>
      </div>
    );
  }

  return null;
}
