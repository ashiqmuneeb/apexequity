import React from 'react';
import { AlertCircle, KeyRound, FolderKanban } from 'lucide-react';

export default function ErrorCard({
  title = 'Error',
  message,
  onConfigureKey,
  onGoToFilings,
  actionLabel,
  onAction,
}) {
  if (!message) return null;

  const isKeyError = typeof message === 'string' && message.includes('GROQ_API_KEY');
  const isDocMissingError =
    typeof message === 'string' &&
    (message.includes('No documents ingested') || message.includes('Filings tab'));

  return (
    <div className="bg-rose-50 border border-rose-200 rounded-2xl p-5 text-sm flex flex-col gap-2.5 shadow-xs transition animate-fade-in">
      <div className="flex items-center gap-2 font-bold text-rose-950 text-sm">
        <AlertCircle className="h-4 w-4 text-rose-700 shrink-0" />
        <span>{title}</span>
      </div>
      <div className="text-slate-800 text-xs sm:text-sm font-medium leading-relaxed">
        {message}
      </div>

      <div className="flex flex-wrap items-center gap-2.5 mt-1">
        {isKeyError && onConfigureKey && (
          <button
            type="button"
            onClick={onConfigureKey}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white hover:bg-rose-100 text-rose-900 border border-rose-300 rounded-xl text-xs font-semibold cursor-pointer transition shadow-xs"
          >
            <KeyRound className="h-3.5 w-3.5 text-rose-700" />
            <span>Configure Groq API Key Now</span>
          </button>
        )}

        {(isDocMissingError || onGoToFilings) && onGoToFilings && (
          <button
            type="button"
            onClick={onGoToFilings}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white hover:bg-blue-50 text-[#01257D] border border-blue-300 rounded-xl text-xs font-bold cursor-pointer transition shadow-xs"
          >
            <FolderKanban className="h-3.5 w-3.5 text-[#01257D]" />
            <span>Open Filings Tab</span>
          </button>
        )}

        {actionLabel && onAction && !onGoToFilings && (
          <button
            type="button"
            onClick={onAction}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 rounded-xl text-xs font-semibold cursor-pointer transition shadow-xs"
          >
            <span>{actionLabel}</span>
          </button>
        )}
      </div>
    </div>
  );
}

