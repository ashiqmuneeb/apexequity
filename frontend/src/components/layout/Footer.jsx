import React from 'react';
import { ShieldCheck, Zap } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200/90 bg-white/70 backdrop-blur-md py-5 text-center text-xs text-slate-600">
      <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-[#01257D]" />
          <span>Local CPU Vector Storage &bull; Form 10-K Audited Grounding</span>
        </div>

        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
          <Zap className="h-3.5 w-3.5 text-[#00A3C4]" />
          <span>Groq LPU Hardware Acceleration</span>
        </div>
      </div>
    </footer>
  );
}
