import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { BarChart3 } from 'lucide-react';

export default function ComparisonChart({ data, stockA, stockB, className = '' }) {
  if (!data || data.length === 0) return null;

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-5 flex flex-col justify-between shadow-xs ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-[#01257D]" />
          <h4 className="text-xs uppercase font-bold tracking-wider text-slate-800">
            Visual Metric Benchmarking: ${stockA} vs ${stockB}
          </h4>
        </div>
        <span className="text-[10px] text-[#01257D] font-mono bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200 font-bold shadow-xs">
          Head-to-Head Normalized
        </span>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 20, left: -10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="metric"
              stroke="#64748b"
              fontSize={12}
              tickLine={false}
            />
            <YAxis stroke="#64748b" fontSize={12} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#ffffff',
                borderColor: '#cbd5e1',
                borderRadius: '0.75rem',
                fontSize: '12px',
                color: '#0f172a',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
              }}
              formatter={(value) => [`${value}`, '']}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
            />
            <Bar
              dataKey={stockA}
              name={`$${stockA}`}
              fill="#01257D"
              radius={[6, 6, 0, 0]}
            />
            <Bar
              dataKey={stockB}
              name={`$${stockB}`}
              fill="#00A3C4"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
