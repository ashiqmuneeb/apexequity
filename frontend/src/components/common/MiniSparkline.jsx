import React from 'react';

export default function MiniSparkline({
  trend = 'up',
  color = null,
  width = 52,
  height = 20,
  className = '',
}) {
  const isUp = trend === 'up';
  const strokeColor = color || (isUp ? '#00FFFF' : '#FF3B5C');
  const gradientId = `sparkline-${Math.random().toString(36).substr(2, 9)}`;

  // Pre-calculated smooth bezier curve paths
  const upPath = 'M2,16 Q14,14 24,10 T40,6 T50,2';
  const upArea = 'M2,16 Q14,14 24,10 T40,6 T50,2 L50,20 L2,20 Z';

  const downPath = 'M2,4 Q14,6 24,11 T40,15 T50,18';
  const downArea = 'M2,4 Q14,6 24,11 T40,15 T50,18 L50,20 L2,20 Z';

  const path = isUp ? upPath : downPath;
  const area = isUp ? upArea : downArea;

  return (
    <div className={`inline-flex items-center ${className}`}>
      <svg
        width={width}
        height={height}
        viewBox="0 0 52 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Gradient Fill under sparkline */}
        <path d={area} fill={`url(#${gradientId})`} />

        {/* Crisp Glow Line */}
        <path
          d={path}
          stroke={strokeColor}
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: `drop-shadow(0 0 3px ${strokeColor}88)` }}
        />

        {/* Terminal Leading Dot */}
        <circle
          cx={50}
          cy={isUp ? 2 : 18}
          r="2"
          fill={strokeColor}
          style={{ filter: `drop-shadow(0 0 4px ${strokeColor})` }}
        />
      </svg>
    </div>
  );
}

