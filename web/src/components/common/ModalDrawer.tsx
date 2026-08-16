import React, { useEffect } from 'react';
import { X, Copy, Check, Terminal, ShieldAlert, FileCode2, ExternalLink } from 'lucide-react';
import { VulnerabilityFinding } from '../../types';
import { SeverityBadge } from './SeverityBadge';

interface ModalDrawerProps {
  finding: VulnerabilityFinding | null;
  onClose: () => void;
}

export const ModalDrawer: React.FC<ModalDrawerProps> = ({ finding, onClose }) => {
  const [copied, setCopied] = React.useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!finding) return null;

  const handleCopyPoc = () => {
    navigator.clipboard.writeText(finding.poc);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-2xl bg-white dark:bg-[#0D121F] border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-start justify-between bg-slate-50/50 dark:bg-[#111827]/50">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={finding.severity} score={finding.cvss_score} />
                <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  {finding.cwe_id} · {finding.category}
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 leading-snug">
                {finding.title}
              </h2>
              <div className="inline-block px-2.5 py-1 bg-slate-100 dark:bg-slate-800/80 rounded font-mono text-xs text-slate-700 dark:text-sky-400 border border-slate-200 dark:border-slate-700/60">
                {finding.endpoint}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Description */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                Description & Vulnerability Impact
              </h3>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-900/40 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800">
                {finding.description}
              </p>
            </div>

            {/* CVSS Vector */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                CVSS 3.1 Vector String
              </h3>
              <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg font-mono text-xs text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span>{finding.cvss_vector}</span>
                <span className="font-semibold text-brand-600 dark:text-brand-400">Score: {finding.cvss_score}</span>
              </div>
            </div>

            {/* PoC Commands */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-brand-500" />
                  Reproducible Proof of Concept (PoC)
                </h3>
                <button
                  onClick={handleCopyPoc}
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy PoC'}
                </button>
              </div>
              <div className="relative rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-900 text-slate-100 p-4 font-mono text-xs leading-relaxed overflow-x-auto">
                <pre className="text-emerald-400">{finding.poc}</pre>
              </div>
            </div>

            {/* Source Code Location (if Whitebox) */}
            {finding.code_locations && finding.code_locations.length > 0 && (
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
                  <FileCode2 className="w-3.5 h-3.5 text-sky-500" />
                  Identified Source Location
                </h3>
                {finding.code_locations.map((loc, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden mb-2">
                    <div className="bg-slate-100 dark:bg-slate-800/80 px-3.5 py-2 text-xs font-mono text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-800 flex justify-between">
                      <span>{loc.file}</span>
                      <span>Lines {loc.start_line}-{loc.end_line}</span>
                    </div>
                    <pre className="p-3.5 bg-slate-50 dark:bg-slate-950/80 font-mono text-xs text-slate-800 dark:text-slate-200 overflow-x-auto">
                      {loc.snippet}
                    </pre>
                  </div>
                ))}
              </div>
            )}

            {/* Remediation Patch */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-emerald-500" />
                Remediation Guidance
              </h3>
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 p-4 font-mono text-xs text-slate-800 dark:text-slate-200 overflow-x-auto whitespace-pre-wrap">
                {finding.remediation_patch}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-[#111827]/50 flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Validated in Kali Linux Sandbox
            </span>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-900 rounded-lg text-xs font-semibold transition-colors"
            >
              Close Inspector
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
