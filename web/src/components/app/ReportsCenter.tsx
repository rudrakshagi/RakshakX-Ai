import React, { useState } from 'react';
import { FileCheck, FileSpreadsheet, FileText, Download, Check, ExternalLink } from 'lucide-react';
import { VulnerabilityFinding } from '../../types';

interface ReportsCenterProps {
  findings: VulnerabilityFinding[];
}

export const ReportsCenter: React.FC<ReportsCenterProps> = ({ findings }) => {
  const [activeExport, setActiveExport] = useState<string | null>(null);

  const handleExport = (type: string) => {
    setActiveExport(type);
    setTimeout(() => setActiveExport(null), 2500);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Compliance & Assessment Reports
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Export confirmed findings in machine-readable and executive formats.
          </p>
        </div>
      </div>

      {/* 3 Large Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* SARIF */}
        <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col justify-between space-y-6">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                OASIS SARIF 2.1.0
              </h3>
              <p className="text-xs text-brand-600 dark:text-brand-400 font-mono mt-0.5">
                GitHub Code Scanning
              </p>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Standard JSON schema for annotating pull requests and integrating with CI/CD security dashboards.
            </p>
          </div>
          <button
            onClick={() => handleExport('sarif')}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-2"
          >
            {activeExport === 'sarif' ? <Check className="w-4 h-4 text-emerald-400" /> : <Download className="w-4 h-4" />}
            <span>{activeExport === 'sarif' ? 'Exported sarif.json' : 'Download SARIF 2.1.0'}</span>
          </button>
        </div>

        {/* PDF */}
        <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col justify-between space-y-6">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-red-50 dark:bg-red-950/50 text-brand-600 dark:text-brand-400 flex items-center justify-center">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                Executive PDF Report
              </h3>
              <p className="text-xs text-brand-600 dark:text-brand-400 font-mono mt-0.5">
                ReportLab Styled Assessment
              </p>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Styled executive summary with CVSS severity breakdown tables, PoC reproduction steps, and strategic remediation.
            </p>
          </div>
          <button
            onClick={() => handleExport('pdf')}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-2"
          >
            {activeExport === 'pdf' ? <Check className="w-4 h-4 text-emerald-400" /> : <Download className="w-4 h-4" />}
            <span>{activeExport === 'pdf' ? 'Generated report.pdf' : 'Download PDF Report'}</span>
          </button>
        </div>

        {/* Markdown */}
        <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col justify-between space-y-6">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-sky-50 dark:bg-sky-950/50 text-sky-600 dark:text-sky-400 flex items-center justify-center">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                Technical Markdown
              </h3>
              <p className="text-xs text-brand-600 dark:text-brand-400 font-mono mt-0.5">
                Developer Remediation
              </p>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Clean markdown document containing code patches, terminal reproduction scripts, and CVSS vector details.
            </p>
          </div>
          <button
            onClick={() => handleExport('md')}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all flex items-center justify-center gap-2"
          >
            {activeExport === 'md' ? <Check className="w-4 h-4 text-emerald-400" /> : <Download className="w-4 h-4" />}
            <span>{activeExport === 'md' ? 'Exported report.md' : 'Download Markdown'}</span>
          </button>
        </div>
      </div>

      {/* Live Markdown Preview Card */}
      <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs space-y-4">
        <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
          Live Report Markdown Preview
        </h3>
        <div className="p-5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 font-mono text-xs text-slate-800 dark:text-slate-200 leading-relaxed overflow-x-auto whitespace-pre-wrap">
{`# RakshakX Security Assessment Report: session_8821

**Target**: https://example.com  
**Mode**: DEEP BLACK-BOX ASSESSMENT  
**Total Verified Findings**: ${findings.length}  

---

## 1. Executive Summary
RakshakX conducted an autonomous multi-agent penetration test against https://example.com. The assessment identified ${findings.filter(f => f.severity === 'critical').length} Critical, ${findings.filter(f => f.severity === 'high').length} High, and ${findings.filter(f => f.severity === 'medium').length} Medium severity vulnerabilities. All findings were dynamically reproduced inside an isolated Kali Linux sandbox.

## 2. Methodology & Observability
All network requests were captured and analyzed through a local Caido HTTP/HTTPS proxy daemon on port 48080. Child agents were coordinated using asynchronous mailboxes.`}
        </div>
      </div>
    </div>
  );
};
