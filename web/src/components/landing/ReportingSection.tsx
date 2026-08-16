import React, { useState } from 'react';
import { FileCheck, FileSpreadsheet, FileText, Download, Check, Sparkles } from 'lucide-react';

export const ReportingSection: React.FC = () => {
  const [downloaded, setDownloaded] = useState<string | null>(null);

  const handleTriggerExport = (type: string) => {
    setDownloaded(type);
    setTimeout(() => setDownloaded(null), 2500);
  };

  return (
    <section id="reporting" className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <FileCheck className="w-3.5 h-3.5 text-brand-500" />
            <span>COMPLIANCE & EXPORTS</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Developer & Executive-Ready Security Reports
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            Export findings in standard formats that plug directly into your engineering pipelines and compliance reviews.
          </p>
        </div>

        {/* 3 Large Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* SARIF Card */}
          <div className="p-7 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-6 hover:border-slate-300 dark:hover:border-slate-700 transition-all">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  OASIS SARIF 2.1.0
                </h3>
                <p className="text-xs text-brand-600 dark:text-brand-400 font-mono mt-0.5">
                  GitHub & GitLab Security Center
                </p>
              </div>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Standard OASIS Static Analysis Results Interchange Format. Upload directly to GitHub Security Center to annotate pull requests with verified vulnerabilities.
              </p>
            </div>
            <button
              onClick={() => handleTriggerExport('sarif')}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-2"
            >
              {downloaded === 'sarif' ? <Check className="w-4 h-4 text-emerald-400" /> : <Download className="w-4 h-4" />}
              <span>{downloaded === 'sarif' ? 'Exported sarif.json' : 'Export SARIF 2.1.0'}</span>
            </button>
          </div>

          {/* PDF Card */}
          <div className="p-7 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-6 hover:border-slate-300 dark:hover:border-slate-700 transition-all">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-red-50 dark:bg-red-950/50 text-brand-600 dark:text-brand-400 flex items-center justify-center">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  Executive PDF Report
                </h3>
                <p className="text-xs text-brand-600 dark:text-brand-400 font-mono mt-0.5">
                  ReportLab Styled Assessment
                </p>
              </div>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Clean executive report with severity metric tables, executive summaries, attack surface breakdown, and strategic remediation recommendations.
              </p>
            </div>
            <button
              onClick={() => handleTriggerExport('pdf')}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-2"
            >
              {downloaded === 'pdf' ? <Check className="w-4 h-4 text-emerald-400" /> : <Download className="w-4 h-4" />}
              <span>{downloaded === 'pdf' ? 'Exported report.pdf' : 'Generate PDF Report'}</span>
            </button>
          </div>

          {/* Markdown Card */}
          <div className="p-7 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-6 hover:border-slate-300 dark:hover:border-slate-700 transition-all">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-sky-50 dark:bg-sky-950/50 text-sky-600 dark:text-sky-400 flex items-center justify-center">
                <FileCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  Technical Markdown
                </h3>
                <p className="text-xs text-brand-600 dark:text-brand-400 font-mono mt-0.5">
                  Developer Remediation & Diff
                </p>
              </div>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Developer-centric markdown document detailing exact curl reproduction steps, impacted parameters, and code patch suggestions.
              </p>
            </div>
            <button
              onClick={() => handleTriggerExport('md')}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-2"
            >
              {downloaded === 'md' ? <Check className="w-4 h-4 text-emerald-400" /> : <Download className="w-4 h-4" />}
              <span>{downloaded === 'md' ? 'Exported report.md' : 'Export Markdown'}</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
