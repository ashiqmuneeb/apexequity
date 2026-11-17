import React, { useState } from 'react';
import { X, ArrowRight, ArrowLeft, CheckCircle2, FileText, Cpu, BarChart3, Sparkles } from 'lucide-react';

export default function OnboardingModal({ isOpen, onClose, onLaunchDemo }) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const steps = [
    {
      stepNumber: 1,
      badge: 'Step 1: Document Grounding',
      title: 'Corporate Filings & Market Ingestion',
      icon: FileText,
      color: 'text-[#01257D] bg-blue-50 border-blue-200 shadow-xs',
      description:
        'Instead of asking generic AI models that guess or hallucinate numbers, ApexEquity ingests verified corporate reports, financial statements, and filing notes directly into a local knowledge vault.',
      bullets: [
        'Stores verified balance sheets, income statements, and footnotes.',
        'Integrates 1-click live market ingestion via Yahoo Finance for any public US stock symbol.',
        'Completely private: filings remain stored on your machine with zero third-party exposure.',
      ],
      tip: 'Pro Tip: You can deposit any custom brokerage report or earnings transcript in the "SEC Filings" tab anytime.',
    },
    {
      stepNumber: 2,
      badge: 'Step 2: High-Speed Semantic Search',
      title: 'Local Vector Embeddings (Zero Cloud API Cost)',
      icon: Cpu,
      color: 'text-[#01257D] bg-blue-50 border-blue-200 shadow-xs',
      description:
        'Every filing is partitioned into contextual text chunks and converted into dense mathematical coordinates using the BAAI/bge-small-en-v1.5 embedding model running locally on your CPU.',
      bullets: [
        'When you select a ticker or ask a question, semantic similarity finds the top matching passages.',
        'Runs 100% locally: zero per-query API bills and works even without internet for vector search.',
        'Automatically avoids redundant re-indexing through persistent StorageContext caching.',
      ],
      tip: 'Pro Tip: Notice the "Context Citations" at the bottom of every report showing the exact source paragraphs used.',
    },
    {
      stepNumber: 3,
      badge: 'Step 3: LPU Acceleration & Visual Reports',
      title: 'Groq AI Inference & Wall Street-Grade Dossiers',
      icon: BarChart3,
      color: 'text-[#01257D] bg-blue-50 border-blue-200 shadow-xs',
      description:
        'Retrieved disclosure chunks are passed to Groq Language Processing Units (LPUs), generating comprehensive financial reports at over 500 words per second.',
      bullets: [
        'Dynamic Financial Health Scorecards: Revenue momentum, YoY growth, and margin breakdown.',
        'Interactive Recharts comparisons for head-to-head peer benchmarking.',
        '1-Click "Print PDF" exports clean, executive-ready research memorandums.',
      ],
      tip: 'Ready to try? Click "Launch Instant Demo" to see NVIDIA analyzed in 0.1 seconds without needing an API key!',
    },
  ];

  const step = steps[currentStep];
  const Icon = step.icon;

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onClose();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden relative">
        
        {/* Header Bar */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-[#01257D] shadow-xs">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">How ApexEquity Works</h3>
              <p className="text-[11px] text-slate-500">30-Second Architecture Walkthrough</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 sm:p-7 space-y-5">
          {/* Progress Indicator */}
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${step.color}`}>
              {step.badge}
            </span>
            <div className="flex items-center gap-1.5">
              {steps.map((_, idx) => (
                <div
                  key={idx}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    idx === currentStep
                      ? 'w-6 bg-[#01257D] shadow-xs'
                      : 'w-2 bg-slate-200'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Step Title & Icon */}
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-[#01257D] shrink-0 shadow-xs">
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-900">{step.title}</h4>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">{step.description}</p>
            </div>
          </div>

          {/* Bullet Highlights */}
          <div className="space-y-2 bg-slate-50 p-4 rounded-xl border border-slate-200">
            {step.bullets.map((b, i) => (
              <div key={i} className="flex items-start gap-2.5 text-xs text-slate-700 leading-relaxed font-medium">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span>{b}</span>
              </div>
            ))}
          </div>

          {/* Tip Callout */}
          <div className="text-[11px] text-[#01257D] bg-blue-50/70 border border-blue-200 px-3.5 py-2 rounded-lg font-semibold">
            💡 {step.tip}
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-500 hover:text-slate-800 transition cursor-pointer font-medium"
          >
            Skip Walkthrough
          </button>

          <div className="flex items-center gap-2.5">
            {currentStep > 0 && (
              <button
                type="button"
                onClick={handleBack}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-200 transition cursor-pointer"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Back</span>
              </button>
            )}

            {currentStep === steps.length - 1 && onLaunchDemo ? (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onLaunchDemo();
                }}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#01257D] hover:bg-[#0244c9] text-white shadow-md transition cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>Launch Instant Demo ($NVDA)</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleNext}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#01257D] hover:bg-[#0244c9] text-white shadow-xs transition cursor-pointer"
              >
                <span>{currentStep === steps.length - 1 ? 'Get Started' : 'Next'}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
