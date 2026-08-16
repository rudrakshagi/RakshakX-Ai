import React from 'react';
import {
  Sparkles,
  Network,
  Box,
  CheckCircle,
  FileCheck2,
  FileSpreadsheet,
  FileText,
  GitPullRequest
} from 'lucide-react';

export const CapabilityStrip: React.FC = () => {
  const capabilities = [
    { icon: Sparkles, label: 'AI-Assisted Analysis' },
    { icon: Network, label: 'Multi-Agent Tree Graph' },
    { icon: Box, label: 'Isolated Kali Sandboxing' },
    { icon: CheckCircle, label: 'Evidence-Based PoCs' },
    { icon: FileCheck2, label: 'CVSS 3.1 Scoring' },
    { icon: FileSpreadsheet, label: 'OASIS SARIF 2.1.0' },
    { icon: FileText, label: 'Executive PDF Reports' },
    { icon: GitPullRequest, label: 'CI/CD PR Blocking' },
  ];

  return (
    <section className="w-full py-8 border-y border-slate-200/80 dark:border-slate-800/80 bg-white/50 dark:bg-slate-900/30 backdrop-blur-xs transition-colors overflow-x-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-6 min-w-max">
          {capabilities.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-slate-700 dark:text-slate-300 text-xs sm:text-sm font-medium hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
              >
                <div className="p-1.5 rounded-md bg-slate-100 dark:bg-slate-800 text-brand-600 dark:text-brand-400">
                  <Icon className="w-4 h-4" />
                </div>
                <span>{item.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
