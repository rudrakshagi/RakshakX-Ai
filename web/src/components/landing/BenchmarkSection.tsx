import React from 'react';

type ScorecardLive = {
  scan_id: string;
  target: string;
  tp: number; fp: number; fn: number;
  total_predictions: number;
  precision: number; recall: number; f1: number; verification_rate: number;
} | null;

export const BenchmarkSection: React.FC<{ scorecard?: ScorecardLive; onViewConsole?: () => void }> = ({ scorecard, onViewConsole }) => {
  return (
    <section className="py-16 bg-white dark:bg-[#0B0F1A] border-y border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-6">
        <div className="inline-flex items-center gap-2 text-xs font-mono tracking-widest text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> RESEARCH / BENCHMARKS
        </div>
        <h2 className="text-3xl font-bold mt-3 text-slate-900 dark:text-white">Benchmark & Validation Protocol v2.0</h2>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300 max-w-3xl">
          Reproducible, evidence-backed measurements of RakshakX Community Edition. See full methodology in{" "}
          <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">docs/BENCHMARK_V2_PROTOCOL.md</span>.
          Detailed results are published under Research / Benchmarks in the product console. The company site shows only a concise verified summary with a link to the full report.
        </p>
        <div className="mt-1 flex items-center gap-2 text-[10px] font-mono">
          <span className={`w-1.5 h-1.5 rounded-full ${scorecard ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
          <span className={scorecard ? 'text-emerald-600' : 'text-amber-600'}>
            {scorecard ? `Live: ${scorecard.scan_id} • ${scorecard.target} • TP ${scorecard.tp} FP ${scorecard.fp} FN ${scorecard.fn}` : 'Offline: showing formula • live via /api/benchmark/scorecard'}
          </span>
        </div>

        <div className="mt-8 grid md:grid-cols-4 gap-4">
          {[
            { k: 'Precision', v: scorecard ? scorecard.precision.toFixed(3) : 'TP/(TP+FP)', d: scorecard ? `TP ${scorecard.tp}` : 'Trustworthiness' },
            { k: 'Recall', v: scorecard ? scorecard.recall.toFixed(3) : 'TP/(TP+FN)', d: scorecard ? `FN ${scorecard.fn}` : 'Coverage' },
            { k: 'F1', v: scorecard ? scorecard.f1.toFixed(3) : '2PR/(P+R)', d: scorecard ? `${scorecard.total_predictions} preds` : 'Balanced score' },
            { k: 'Verification Rate', v: scorecard ? scorecard.verification_rate.toFixed(3) : 'Confirmed/candidates', d: scorecard ? `${scorecard.verification_rate.toFixed(2)}` : 'Evidence quality' },
          ].map(c => (
            <div key={c.k} className="rounded-2xl border border-slate-200 dark:border-slate-800 p-5 bg-slate-50 dark:bg-[#121B2D]">
              <div className="text-xs font-bold tracking-widest text-slate-500">{c.k}</div>
              <div className="font-mono text-sm mt-1">{c.v}</div>
              <div className="text-xs text-slate-500 mt-1">{c.d}</div>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 p-5 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
          <span className="font-bold">Integrity Statement:</span> The benchmark measures RakshakX on selected controlled environments and does not establish universal vulnerability detection, zero-day detection, enterprise-scale performance, or security of arbitrary real-world systems.
        </div>

        <div className="mt-6 flex flex-wrap gap-3 text-xs">
          {onViewConsole ? (
            <button onClick={onViewConsole} className="px-4 py-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-semibold">View Benchmarks in Console →</button>
          ) : (
            <a href="#benchmark" className="px-4 py-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-semibold">View Benchmarks in Console →</a>
          )}
          <span className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">Primary: Juice Shop 17.2.1 · DVWA 2.0 · Metasploitable2</span>
        </div>
      </div>
    </section>
  );
};
