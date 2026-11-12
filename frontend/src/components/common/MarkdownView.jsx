import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MarkdownView({ content }) {
  if (!content) return null;

  return (
    <div className="prose max-w-none text-slate-800 leading-relaxed space-y-4">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-2xl font-bold text-slate-900 border-b border-slate-200 pb-2 mt-6 mb-3 flex items-center gap-2" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xl font-bold text-[#01257D] mt-5 mb-2 border-b border-slate-200 pb-1" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-lg font-bold text-slate-900 mt-4 mb-2" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="text-slate-700 my-2 leading-relaxed" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-outside pl-6 space-y-1.5 text-slate-700 my-3" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-outside pl-6 space-y-1.5 text-slate-700 my-3" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="leading-relaxed" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-slate-900" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="text-slate-600 italic" {...props} />
          ),
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-4 border-[#01257D] bg-blue-50/50 px-4 py-2 italic text-slate-700 rounded-r-md my-3" {...props} />
          ),
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4 border border-slate-200 rounded-lg shadow-xs">
              <table className="min-w-full divide-y divide-slate-200 text-sm" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-slate-100 text-slate-900 font-bold text-left" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="px-4 py-2.5 text-xs uppercase tracking-wider text-[#01257D] font-bold" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-4 py-2.5 border-t border-slate-200 text-slate-700" {...props} />
          ),
          code: ({ node, inline, ...props }) => (
            inline ? (
              <code className="bg-slate-100 text-[#01257D] px-1.5 py-0.5 rounded text-xs font-mono border border-slate-200 font-bold" {...props} />
            ) : (
              <code className="block bg-slate-900 text-slate-100 p-4 rounded-xl overflow-x-auto text-xs font-mono shadow-xs" {...props} />
            )
          ),
          hr: ({ node, ...props }) => (
            <hr className="border-slate-200 my-6" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
