import React, { useState } from 'react';
import { Key, X, ExternalLink, Check, AlertCircle } from 'lucide-react';

export default function ApiKeyModal({ isOpen, onClose, onSaveKey, currentHasKey }) {
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError('Please enter a valid Groq API key.');
      return;
    }

    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await onSaveKey(apiKey.trim());
      setMessage('Groq API Key saved successfully!');
      setApiKey('');
      setTimeout(() => {
        onClose();
        setMessage(null);
      }, 1200);
    } catch (err) {
      setError(err.message || 'Failed to update Groq API key');
    } finally {
      setSaving(false);
    }
  };

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
            <h3 className="text-base font-bold text-slate-900">Groq API Key</h3>
            <p className="text-xs text-slate-500">Powers sub-second Llama 3.3 70B financial inference</p>
          </div>
        </div>

        <p className="text-xs text-slate-600 mb-4 leading-relaxed">
          Groq provides blazing-fast deterministic inference with a generous free tier. Get a key in 30 seconds from Groq Console.
        </p>

        <a
          href="https://console.groq.com/keys"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-[#01257D] hover:underline font-bold mb-4 group"
        >
          <span>Get Free Groq API Key</span>
          <ExternalLink className="h-3 w-3 group-hover:translate-x-0.5 transition" />
        </a>

        {currentHasKey && (
          <div className="mb-4 flex items-center gap-2 p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-[#01257D] text-xs font-semibold">
            <Check className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>A Groq API key is already configured on the server.</span>
          </div>
        )}

        {message && (
          <div className="mb-4 flex items-center gap-2 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
            <Check className="h-4 w-4" />
            <span>{message}</span>
          </div>
        )}

        {error && (
          <div className="mb-4 flex items-center gap-2 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              API Key (gsk_...)
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="gsk_xxxxxxxxxxxxxxxxxxxxxxxx"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#01257D]/30 focus:border-[#01257D] font-mono transition"
            />
          </div>

          <div className="flex justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 border border-slate-200 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !apiKey.trim()}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#01257D] via-[#0244c9] to-[#00A3C4] hover:opacity-95 transition shadow-sm disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
            >
              {saving ? 'Saving...' : 'Save API Key'}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
