import React from 'react';
import { ArrowRight, Github, Shield } from 'lucide-react';

interface FinalCtaSectionProps {
  onStartScan: () => void;
}

export const FinalCtaSection: React.FC<FinalCtaSectionProps> = ({ onStartScan }) => {
  return (
    <section className="py-24 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors relative overflow-hidden">
      {/* Background Accent */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-brand-500/5 to-transparent pointer-events-none -z-10" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center mx-auto shadow-lg shadow-brand-500/20">
          <Shield className="w-6 h-6" />
        </div>

        <div className="space-y-4 max-w-2xl mx-auto">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight">
            Build Safer Systems With RakshakX
          </h2>
          <p className="text-lg text-slate-600 dark:text-slate-300 font-medium">
            Analyze. Verify. Understand. Secure.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <button
            onClick={onStartScan}
            className="inline-flex items-center gap-2 px-7 py-4 rounded-xl font-bold text-sm text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 shadow-md shadow-brand-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <span>Start A Security Scan</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <a
            href="https://github.com/rakshakx/rakshakx"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-7 py-4 rounded-xl font-semibold text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 shadow-xs transition-all"
          >
            <Github className="w-4 h-4" />
            <span>View On GitHub</span>
          </a>
        </div>
      </div>
    </section>
  );
};
