import React from 'react';

export default function LoadingSkeleton({ text = 'Querying vector embeddings & Groq Llama-3.3-70b...' }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-8 space-y-4 animate-pulse shadow-sm">
      <div className="h-6 bg-slate-200 rounded-md w-1/3" />
      <div className="h-4 bg-slate-100 rounded-md w-full" />
      <div className="h-4 bg-slate-100 rounded-md w-5/6" />
      <div className="h-4 bg-slate-100 rounded-md w-4/6" />
      <div className="pt-4 space-y-2">
        <div className="h-5 bg-slate-200 rounded-md w-1/4" />
        <div className="h-4 bg-slate-100 rounded-md w-full" />
        <div className="h-4 bg-slate-100 rounded-md w-11/12" />
      </div>
      <div className="text-center text-xs text-[#01257D] pt-2 font-mono flex items-center justify-center gap-2 font-bold">
        <div className="h-2 w-2 rounded-full bg-[#01257D] animate-ping" />
        <span>{text}</span>
      </div>
    </div>
  );
}
