import React, { useState } from 'react';
import { SlidersHorizontal, Calculator, Check, Shield } from 'lucide-react';

export const CvssRiskSection: React.FC = () => {
  const [metrics, setMetrics] = useState({
    av: 'Network',
    ac: 'Low',
    pr: 'None',
    ui: 'None',
    s: 'Unchanged',
    c: 'High',
    i: 'High',
    a: 'None'
  });

  return (
    <section className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Description */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
              <Calculator className="w-3.5 h-3.5 text-brand-500" />
              <span>QUANTITATIVE SCORING</span>
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight">
              Standardized CVSS 3.1 Metric Scoring
            </h2>

            <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed">
              Every verified vulnerability is scored against the official FIRST CVSS v3.1 specification. The engine generates reproducible vector strings ready for enterprise triage.
            </p>

            {/* Severity Threshold Strip */}
            <div className="space-y-2 pt-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Severity Score Bands
              </div>
              <div className="grid grid-cols-4 gap-2 text-center text-xs font-semibold">
                <div className="p-2 rounded-lg bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/60">
                  <div className="font-bold">Critical</div>
                  <div className="text-[10px] opacity-80">9.0 - 10.0</div>
                </div>
                <div className="p-2 rounded-lg bg-orange-50 dark:bg-orange-950/40 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-900/60">
                  <div className="font-bold">High</div>
                  <div className="text-[10px] opacity-80">7.0 - 8.9</div>
                </div>
                <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/60">
                  <div className="font-bold">Medium</div>
                  <div className="text-[10px] opacity-80">4.0 - 6.9</div>
                </div>
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-900/60">
                  <div className="font-bold">Low</div>
                  <div className="text-[10px] opacity-80">0.1 - 3.9</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Live Interactive CVSS Calculator Card */}
          <div className="lg:col-span-7">
            <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 shadow-md space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Calculated Base Score
                  </div>
                  <div className="text-3xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2 mt-1">
                    <span>9.8</span>
                    <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-red-100 dark:bg-red-950 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900">
                      CRITICAL
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    CVSS Vector
                  </div>
                  <div className="font-mono text-xs text-brand-600 dark:text-brand-400 font-semibold mt-1">
                    CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
                  </div>
                </div>
              </div>

              {/* Vector Metric Pills Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Attack Vector (AV)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">Network (N)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Complexity (AC)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">Low (L)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Privileges (PR)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">None (N)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">User Interaction (UI)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">None (N)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Scope (S)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">Unchanged (U)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Confidentiality (C)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">High (H)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Integrity (I)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">High (H)</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Availability (A)</div>
                  <div className="font-bold text-slate-900 dark:text-slate-100 mt-1">High (H)</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
