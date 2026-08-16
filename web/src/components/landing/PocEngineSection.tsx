import React from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Fingerprint,
  Terminal,
  FileCheck2
} from 'lucide-react';

export const PocEngineSection: React.FC = () => {
  return (
    <section className="py-20 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <ShieldCheck className="w-3.5 h-3.5 text-brand-500" />
            <span>EMPIRICAL VERIFICATION</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Evidence Before Confidence: "PoC Or It Didn't Happen"
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            Unlike static code scanners that generate hundreds of unverified warnings, RakshakX never reports a finding solely because an LLM guessed it exists.
          </p>
        </div>

        {/* Verification Logic Box */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left: 5-Stage Verification Pipeline */}
          <div className="lg:col-span-7 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 p-6 space-y-6 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Deterministic PoC Validation Workflow
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs sm:text-sm">
                <span className="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center font-bold text-xs">1</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">Potential Finding Identified</span>
                <span className="text-slate-400 ml-auto text-xs">Hypothesis</span>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs sm:text-sm">
                <span className="w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-950 text-brand-600 flex items-center justify-center font-bold text-xs">2</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">Reproduction Command Synthesized</span>
                <span className="text-slate-400 ml-auto text-xs">curl / python script</span>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs sm:text-sm">
                <span className="w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-600 flex items-center justify-center font-bold text-xs">3</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">Dynamic Sandbox Execution</span>
                <span className="text-slate-400 ml-auto text-xs">Kali Linux isolated exec</span>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs sm:text-sm">
                <span className="w-6 h-6 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-600 flex items-center justify-center font-bold text-xs">4</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">Evidence Output Captured</span>
                <span className="text-slate-400 ml-auto text-xs">Response time / body diff</span>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900 text-white dark:bg-brand-600 border border-slate-900 dark:border-brand-500 text-xs sm:text-sm font-semibold shadow-md">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>Confirmed & Filed via create_vulnerability_report()</span>
                <span className="text-white/80 ml-auto text-xs">0% False Positive</span>
              </div>
            </div>

            {/* Deduplication Callout */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center gap-3 text-xs text-slate-600 dark:text-slate-400">
              <Fingerprint className="w-4 h-4 text-brand-500 shrink-0" />
              <div>
                <strong>Composite Hash Deduplication:</strong> Normalized URLs + CWE categories generate SHA-256 fingerprint hashes to prevent alert spam across duplicate routes.
              </div>
            </div>
          </div>

          {/* Right: Concrete Verified Finding Card Example */}
          <div className="lg:col-span-5 space-y-4">
            <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 shadow-md space-y-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-orange-50 dark:bg-orange-950/40 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-900 text-xs font-bold uppercase">
                  HIGH · CVSS 8.6
                </span>
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  VERIFIED POC
                </span>
              </div>

              <div>
                <h4 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Time-Based Blind SQL Injection
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                  example.com/api/v1/catalog/search
                </p>
              </div>

              <div className="space-y-1.5">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                  Verified Sandbox Command
                </div>
                <div className="p-3 bg-slate-900 text-emerald-400 rounded-xl font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800">
                  <code>curl -i -s "https://example.com/api/v1/catalog/search?q=test'%20OR%20(SELECT%20pg_sleep(5))--%20-"</code>
                </div>
              </div>

              <div className="pt-2 text-xs text-slate-600 dark:text-slate-400 flex items-center justify-between border-t border-slate-100 dark:border-slate-800">
                <span>Confidence: <strong>High (Reproducible)</strong></span>
                <span>Response Delta: <strong>5.04s</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
