import React, { useState, useEffect } from 'react';

/**
 * Animated number count-up hook & component
 * Animates numerical values with prefix/suffix preservation.
 */
export default function AnimatedCounter({ value, duration = 800, className = '' }) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    if (!value) {
      setDisplayValue(value);
      return;
    }

    // Extract numbers, decimals, and surrounding text (e.g., "$22.1B", "+265%", "76.0%")
    const str = String(value);
    const match = str.match(/([^\d.-]*)([\d.-]+)([^\d.-]*)/);

    if (!match) {
      setDisplayValue(value);
      return;
    }

    const prefix = match[1] || '';
    const num = parseFloat(match[2]);
    const suffix = match[3] || '';

    if (isNaN(num)) {
      setDisplayValue(value);
      return;
    }

    const hasDecimal = match[2].includes('.');
    const decimalPlaces = hasDecimal ? match[2].split('.')[1].length : 0;

    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const currentNum = num * eased;

      setDisplayValue(`${prefix}${currentNum.toFixed(decimalPlaces)}${suffix}`);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(str);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return <span className={className}>{displayValue}</span>;
}

