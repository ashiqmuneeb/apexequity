import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

export default function InfoTooltip({ text, title, position = 'top' }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <span className="relative inline-flex items-center ml-1">
      <button
        type="button"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        className="text-slate-400 hover:text-cyan-400 transition cursor-help p-0.5"
        aria-label="More information"
      >
        <HelpCircle className="h-3 w-3" />
      </button>

      {isVisible && (
        <span
          className={`absolute z-50 w-56 p-2.5 text-[11px] leading-relaxed text-slate-200 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl backdrop-blur-md pointer-events-none transition duration-150 ${
            position === 'top'
              ? 'bottom-full left-1/2 -translate-x-1/2 mb-2'
              : position === 'bottom'
              ? 'top-full left-1/2 -translate-x-1/2 mt-2'
              : 'left-full top-1/2 -translate-y-1/2 ml-2'
          }`}
        >
          {title && (
            <span className="block font-semibold text-cyan-300 text-xs mb-1">
              {title}
            </span>
          )}
          <span className="block font-normal text-slate-300">
            {text}
          </span>
          <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
        </span>
      )}
    </span>
  );
}

