import React from 'react';
import { Key, X, ExternalLink, Check, ShieldCheck } from 'lucide-react';

export default function ApiKeyModal({ isOpen, onClose, currentHasKey }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-md shadow-2xl p-6 relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-[#01257D] shadow-xs">
            <Key className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Groq API Configuration</h3>
            <p className="text-xs text-slate-500">Hardware-accelerated AI inference engine</p>
          </div>
        </div>

        <p className="text-xs text-slate-600 mb-4 leading-relaxed">
          For institutional security, API keys are managed exclusively via environment variables and are never written to disk from web endpoints.
        </p>

        {currentHasKey ? (
          <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>Groq API Key is active and loaded from the server environment (.env).</span>
          </div>
        ) : (
          <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs space-y-1.5">
            <div className="font-bold flex items-center gap-1.5">
              <span>Key not found in server environment</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Add your key to <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">backend/.env</code>:
            </p>
            <pre className="bg-slate-900 text-slate-100 p-2 rounded-lg text-[10px] font-mono select-all">
              GROQ_API_KEY=gsk_your_key_here
            </pre>
          </div>
        )}

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-2 mb-4">
          <span className="font-semibold text-slate-800 block">How to obtain a free key:</span>
          <p className="text-[11px] leading-relaxed">
            Groq provides deterministic inference with high rate limits on its developer free tier.
          </p>
          <a
            href="https://console.groq.com/keys"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[#01257D] hover:underline font-bold"
          >
            <span>Open Groq Cloud Console</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#01257D] hover:bg-[#023b9c] transition shadow-xs cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
