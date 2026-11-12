import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { Award } from 'lucide-react';

export default function MoatRadarChart({ stockA = 'NVDA', stockB = 'GOOGL', className = '' }) {
  // 5-Axis normalized quantitative scores (0-100)
  const defaultScores = {
    NVDA: { growth: 99, margin: 96, balance: 88, moat: 98, reg: 74 },
    GOOGL: { growth: 82, margin: 85, balance: 95, moat: 94, reg: 70 },
    MSFT: { growth: 86, margin: 91, balance: 96, moat: 95, reg: 78 },
    AAPL: { growth: 76, margin: 82, balance: 98, moat: 96, reg: 72 },
  };

  const aScores = defaultScores[stockA] || { growth: 85, margin: 82, balance: 88, moat: 90, reg: 75 };
  const bScores = defaultScores[stockB] || { growth: 80, margin: 80, balance: 90, moat: 88, reg: 75 };

  const data = [
    { subject: 'Top-Line Velocity', [stockA]: aScores.growth, [stockB]: bScores.growth, fullMark: 100 },
    { subject: 'Pricing Power (Margin)', [stockA]: aScores.margin, [stockB]: bScores.margin, fullMark: 100 },
    { subject: 'Balance Sheet Fortress', [stockA]: aScores.balance, [stockB]: bScores.balance, fullMark: 100 },
    { subject: 'Software Ecosystem Moat', [stockA]: aScores.moat, [stockB]: bScores.moat, fullMark: 100 },
    { subject: 'Regulatory Resilience', [stockA]: aScores.reg, [stockB]: bScores.reg, fullMark: 100 },
  ];

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-5 flex flex-col justify-between shadow-xs ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Award className="h-4 w-4 text-[#01257D]" />
          <h4 className="text-xs uppercase font-bold tracking-wider text-slate-800">
            5-Axis Moat &amp; Resilience Radar
          </h4>
        </div>
        <span className="text-[10px] text-[#01257D] font-mono bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200 font-bold shadow-xs">
          Polygonal Benchmark
        </span>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid stroke="#e2e8f0" strokeOpacity={1} />
            <PolarAngleAxis
              dataKey="subject"
              stroke="#64748b"
              tick={{ fill: '#334155', fontSize: 10, fontWeight: 600 }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 100]}
              stroke="#cbd5e1"
              tick={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#ffffff',
                borderColor: '#cbd5e1',
                borderRadius: '0.75rem',
                fontSize: '11px',
                color: '#0f172a',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
              }}
              formatter={(value) => [`${value} / 100`, '']}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
            <Radar
              name={`$${stockA} (Primary)`}
              dataKey={stockA}
              stroke="#01257D"
              fill="#01257D"
              fillOpacity={0.22}
              strokeWidth={2}
            />
            <Radar
              name={`$${stockB} (Benchmark)`}
              dataKey={stockB}
              stroke="#00A3C4"
              fill="#00A3C4"
              fillOpacity={0.22}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="pt-2.5 border-t border-slate-200 flex items-center justify-between text-[10px] font-mono text-slate-500">
        <span>Dual 10-K Quantitative Scores</span>
        <div className="flex items-center gap-3">
          <span className="text-[#01257D] font-bold">${stockA} Advantage</span>
          <span className="text-[#00A3C4] font-bold">${stockB} Advantage</span>
        </div>
      </div>
    </div>
  );
}
