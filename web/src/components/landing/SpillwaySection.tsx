import React from 'react';
import { HardDrive, ArrowRight, FileText, Terminal, Layers } from 'lucide-react';

export const SpillwaySection: React.FC = () => {
  return (
    <section className="py-20 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Diagram */}
          <div className="lg:col-span-7">
            <div className="p-6 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Spillway Output Bounding Architecture
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center text-xs">
                <div className="p-4 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 space-y-2">
                  <div className="text-red-500 font-bold font-mono">50,000+ Lines</div>
                  <div className="text-slate-600 dark:text-slate-400">Raw Nmap / FFuF Output</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 text-white dark:bg-brand-600 border border-slate-900 dark:border-brand-500 space-y-2 shadow-md">
                  <div className="font-bold font-mono">Spillway Storage</div>
                  <div className="text-white/80 text-[11px]">/workspace/.rakshak/spill/</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 space-y-2">
                  <div className="text-emerald-500 font-bold font-mono">100-Line Preview</div>
                  <div className="text-slate-600 dark:text-slate-400">Fed to LLM Reasoner</div>
                </div>
              </div>

              {/* Sample output representation */}
              <div className="p-4 rounded-xl bg-slate-900 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800">
                <div className="text-amber-400">[!] Output exceeded 2,000 characters. Spilled full dump to disk:</div>
                <div className="text-sky-400">Path: /workspace/.rakshak/spill/spill_8f9a12c4.txt (4.2 MB)</div>
                <div className="text-slate-500 mt-2">--- PREVIEW (Lines 1-10) ---</div>
                <div className="text-slate-400"># Nmap 7.94 scan initiated... 42 open ports discovered</div>
              </div>
            </div>
          </div>

          {/* Right Description */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
              <HardDrive className="w-3.5 h-3.5 text-brand-500" />
              <span>OUTPUT STORE SPILLWAY</span>
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight">
              Intelligent Output Bounding & Spillway Store
            </h2>

            <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed">
              Bruteforcing tools and port scanners can produce megabytes of verbose output. Rather than flooding the reasoning context, RakshakX intercepts large dumps, stores them on the sandbox disk, and supplies the agent with a concise preview plus file pointer.
            </p>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400">
              <strong>Result:</strong> Zero LLM context pollution, maximum reasoning bandwidth, and 100% full log retention on disk.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
