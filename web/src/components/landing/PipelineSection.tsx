import React, { useState } from 'react';
import { PIPELINE_STAGES } from '../../data/mockScanData';
import { Layers, ArrowRight, Terminal, Wrench } from 'lucide-react';

export const PipelineSection: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const current = PIPELINE_STAGES[activeStep];

  return (
    <section id="pipeline" className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <Layers className="w-3.5 h-3.5 text-brand-500" />
            <span>ANALYSIS LIFECYCLE</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            The 8-Stage Security Analysis Pipeline
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            Every target progresses through a deterministic, empirical verification pipeline from scope intake to compliance reporting.
          </p>
        </div>

        {/* 8-Step Interactive Pipeline Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 mb-8">
          {PIPELINE_STAGES.map((stage, idx) => {
            const isActive = activeStep === idx;
            return (
              <button
                key={stage.id}
                onClick={() => setActiveStep(idx)}
                className={`p-3 rounded-xl border text-left transition-all relative flex flex-col justify-between ${
                  isActive
                    ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-md scale-102 z-10'
                    : 'bg-white dark:bg-[#0E1524] text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <span className={`font-mono text-xs font-bold ${isActive ? 'text-brand-300' : 'text-slate-400'}`}>
                    {stage.number}
                  </span>
                  <span className={`text-[10px] uppercase font-semibold px-1.5 py-0.2 rounded ${
                    isActive ? 'bg-white/20 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                  }`}>
                    {stage.badge}
                  </span>
                </div>
                <div className="font-bold text-xs leading-snug truncate">{stage.title}</div>
              </button>
            );
          })}
        </div>

        {/* Active Stage Technical Detail Card */}
        <div className="rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 p-8 shadow-sm transition-all">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xl font-extrabold text-brand-600 dark:text-brand-400">
                  STAGE {current.number}
                </span>
                <span className="text-slate-300 dark:text-slate-700">·</span>
                <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {current.title}
                </h3>
              </div>

              <div className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                {current.summary}
              </div>

              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {current.details}
              </p>

              <div className="pt-2 flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
                <Wrench className="w-3.5 h-3.5 text-brand-500" />
                <span>Underlying Engine Tool: <strong>{current.tool}</strong></span>
              </div>
            </div>

            <div className="lg:col-span-5 bg-slate-50 dark:bg-[#121B2D] p-5 rounded-xl border border-slate-200 dark:border-slate-700/80 space-y-3 font-mono text-xs">
              <div className="text-[11px] uppercase font-bold text-slate-400 dark:text-slate-500 flex items-center justify-between">
                <span>Stage Execution Artifact</span>
                <span className="text-emerald-600 dark:text-emerald-400">Status: PASS</span>
              </div>
              <div className="p-3 bg-slate-900 text-sky-400 rounded-lg overflow-x-auto leading-relaxed">
                <div>[+] Initialized pipeline stage: {current.title}</div>
                <div>[+] Engine: {current.tool}</div>
                <div>[+] Output validated with zero false positives.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
