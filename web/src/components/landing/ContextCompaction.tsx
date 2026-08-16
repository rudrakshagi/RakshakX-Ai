import React from 'react';
import { Sparkles, Brain, ArrowDown, FileArchive, CheckCircle2 } from 'lucide-react';

export const ContextCompaction: React.FC = () => {
  return (
    <section className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Description */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
              <Brain className="w-3.5 h-3.5 text-brand-500" />
              <span>TOKEN RESILIENCE</span>
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight">
              Built For Long-Running Security Analysis
            </h2>

            <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed">
              Complex security audits can require hundreds of reasoning turns. When token limits approach capacity, RakshakX converts conversational history into dense, factual security checkpoints instead of crashing.
            </p>

            <div className="space-y-3 pt-2 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>Retains system prompt and active credentials verbatim</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>Compresses 100+ turns into structured &lt;conversation-checkpoint&gt;</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>Zero loss of verified vulnerabilities or attack surface maps</span>
              </div>
            </div>
          </div>

          {/* Right Visual Flow Card */}
          <div className="lg:col-span-7">
            <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 shadow-md space-y-4">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                <span>compaction.py · Checkpoint Engine</span>
                <span className="text-emerald-500 font-semibold">Active Memory Compression</span>
              </div>

              {/* Step 1: Raw Stream */}
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs">
                <div>
                  <div className="font-bold text-slate-900 dark:text-slate-100">120+ Agent Conversation Turns</div>
                  <div className="text-slate-500">Approaching 128k context token limit</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-red-100 dark:bg-red-950 text-red-600 dark:text-red-400 font-mono text-[11px] font-bold">
                  Context Overflow Risk
                </span>
              </div>

              <div className="flex justify-center text-slate-400">
                <ArrowDown className="w-4 h-4 animate-bounce" />
              </div>

              {/* Step 2: Checkpoint Output */}
              <div className="p-4 rounded-xl bg-slate-900 text-sky-400 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800 space-y-1">
                <div className="text-slate-400">&lt;conversation-checkpoint&gt;</div>
                <div className="text-emerald-400">Target: https://example.com | Scope: 42 Endpoints</div>
                <div>Discovered Auth: Bearer eyJhbGci...</div>
                <div>Verified Vulnerabilities: [VULN-001 (JWT), VULN-002 (SQLi)]</div>
                <div>Pending Tasks: Concurrency testing on /api/v1/coupons</div>
                <div className="text-slate-400">&lt;/conversation-checkpoint&gt;</div>
              </div>

              <div className="text-xs text-center text-slate-500 dark:text-slate-400 pt-1">
                Context compressed by <strong>86%</strong> · Scan continues uninterrupted.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
