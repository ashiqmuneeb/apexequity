import React from 'react';
import { HelpCircle, ArrowRight } from 'lucide-react';

const TICKER_QUESTIONS = {
  NVDA: [
    'What is Nvidia’s primary supply chain dependency on TSMC and CoWoS packaging?',
    'How do US export control revisions on China affect future Data Center guidance?',
    'Compare Hopper vs Blackwell architecture pricing power and enterprise TAM.',
  ],
  GOOGL: [
    'What are the primary antitrust litigation risks facing Google Search and ad tech?',
    'How does Google Cloud Platform (GCP) operating margin compare to AWS and Azure?',
    'What is Alphabet’s annual capital expenditure trajectory on Gemini infrastructure?',
  ],
  MSFT: [
    'What is Microsoft Azure’s revenue contribution from OpenAI enterprise workloads?',
    'How is Copilot commercial pricing impacting Office 365 Average Revenue Per User (ARPU)?',
    'What are the primary regulatory commitments following the Activision Blizzard acquisition?',
  ],
  AAPL: [
    'What is Apple’s revenue diversification strategy between iPhone and Services margin expansion?',
    'How will European Digital Markets Act (DMA) compliance affect App Store commission rates?',
    'What is Apple’s hardware roadmap for Apple Intelligence on-device neural engines?',
  ],
  DEFAULT: [
    'What are the primary material risk disclosures in the latest SEC Form 10-K filing?',
    'How has the operating margin and free cash flow profile evolved over the past 4 quarters?',
    'What is management’s guidance regarding capital expenditure and market share defense?',
  ],
};

export default function FollowUpQuestions({ ticker, onSelectQuestion }) {
  const symbol = (ticker || '').toUpperCase();
  const questions = TICKER_QUESTIONS[symbol] || TICKER_QUESTIONS.DEFAULT;

  return (
    <div className="mt-6 pt-5 border-t border-slate-200">
      <div className="flex items-center gap-2 mb-3">
        <HelpCircle className="h-4 w-4 text-[#01257D]" />
        <h4 className="text-xs uppercase font-bold tracking-wider text-slate-800">
          Suggested Follow-Up Inquiries for ${symbol || 'TICKER'}
        </h4>
        <span className="text-[10px] text-[#01257D] font-mono bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200 font-bold shadow-xs">
          1-Click Deep Dive
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {questions.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectQuestion && onSelectQuestion(q)}
            className="text-left p-3.5 rounded-xl bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#01257D]/40 text-xs text-slate-700 hover:text-slate-900 transition group flex flex-col justify-between cursor-pointer shadow-xs hover:shadow-md"
          >
            <p className="line-clamp-2 leading-relaxed font-medium">
              "{q}"
            </p>
            <div className="mt-2.5 flex items-center justify-end text-[11px] font-bold text-[#01257D] group-hover:translate-x-0.5 transition">
              <span className="mr-1">Analyze Query</span>
              <ArrowRight className="h-3 w-3" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
