import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function ErrorCard({ title = 'Error', message, onConfigureKey }) {
  if (!message) return null;

  const isKeyError = typeof message === 'string' && message.includes('GROQ_API_KEY');

  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5 text-sm text-red-300 flex flex-col gap-2">
      <div className="flex items-center gap-2 font-semibold text-red-200">
        <AlertCircle className="h-4 w-4" />
        <span>{title}</span>
      </div>
      <div>{message}</div>
      {isKeyError && onConfigureKey && (
        <button
          onClick={onConfigureKey}
          className="self-start mt-2 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/40 rounded-lg text-xs font-medium cursor-pointer transition"
        >
          Configure Groq API Key Now
        </button>
      )}
    </div>
  );
}

