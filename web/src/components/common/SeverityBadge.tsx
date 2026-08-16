import React from 'react';
import { SeverityLevel } from '../../types';

interface SeverityBadgeProps {
  severity: SeverityLevel;
  score?: number;
  showScore?: boolean;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  score,
  showScore = true,
  className = '',
}) => {
  const styles: Record<SeverityLevel, { bg: string; text: string; border: string }> = {
    critical: {
      bg: 'bg-red-50 dark:bg-red-950/40',
      text: 'text-red-700 dark:text-red-400',
      border: 'border-red-200 dark:border-red-900/60',
    },
    high: {
      bg: 'bg-orange-50 dark:bg-orange-950/40',
      text: 'text-orange-700 dark:text-orange-400',
      border: 'border-orange-200 dark:border-orange-900/60',
    },
    medium: {
      bg: 'bg-amber-50 dark:bg-amber-950/40',
      text: 'text-amber-700 dark:text-amber-400',
      border: 'border-amber-200 dark:border-amber-900/60',
    },
    low: {
      bg: 'bg-blue-50 dark:bg-blue-950/40',
      text: 'text-blue-700 dark:text-blue-400',
      border: 'border-blue-200 dark:border-blue-900/60',
    },
    info: {
      bg: 'bg-slate-50 dark:bg-slate-900/40',
      text: 'text-slate-700 dark:text-slate-400',
      border: 'border-slate-200 dark:border-slate-800',
    },
  };

  const style = styles[severity] || styles.medium;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wider border ${style.bg} ${style.text} ${style.border} ${className}`}
    >
      <span>{severity}</span>
      {showScore && score !== undefined && (
        <span className="font-mono opacity-80">· {score.toFixed(1)}</span>
      )}
    </span>
  );
};
