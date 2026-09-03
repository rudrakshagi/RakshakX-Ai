import React, { useEffect, useState } from 'react';

type Scorecard = {
  protocol_version: string;
  scan_id: string;
  target: string;
  total_reference: number;
  total_predictions: number;
  tp: number; fp: number; fn: number; tn: number;
  precision: number; recall: number; f1: number;
  verification_rate: number;
  assessment_time_s: number;
};

export const BenchmarksView: React.FC = () => {
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [freeze, setFreeze] = useState<any | null>(null);
  const [repeat, setRepeat] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<string>('');

  useEffect(() => {
    fetch('/api/runs').then(r => r.ok ? r.json() : []).then(list => {
      if (Array.isArray(list) && list.length > 0) {
        setRuns(list);
        if (!selectedRun) setSelectedRun(list[0].id);
      }
    }).catch(()=>{});
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const q = selectedRun ? `?run=${encodeURIComponent(selectedRun)}` : '';
        const [scRes, frRes, rpRes] = await Promise.all([
          fetch(`/api/benchmark/scorecard${q}`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`/api/benchmark/freeze${q}`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch('/api/benchmark/repeatability').then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        // reset before set to avoid stale
        setScorecard(null); setFreeze(null);
        if (scRes && !scRes.error) setScorecard(scRes);
        if (frRes && !frRes.error) setFreeze(frRes);
        if (rpRes && !rpRes.error) setRepeat(rpRes);
        if (!scRes && !frRes && !rpRes) setErr('No benchmark artifacts yet. Run a benchmark scan or scripts/run_benchmark_v2.py');
        else setErr(null);
      } catch (e: any) {
        setErr(String(e));
      }
    }
    load();
  }, [selectedRun]);

  const integrity = "The benchmark measures RakshakX on selected controlled environments and does not establish universal vulnerability detection, zero-day detection, enterprise-scale performance, or security of arbitrary real-world systems.";

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {runs.length > 0 && (
        <div className="flex items-center gap-2 justify-end">
          <span className="text-xs font-semibold text-slate-500">Benchmark Run:</span>
          <select value={selectedRun} onChange={e => setSelectedRun(e.target.value)} className="px-3 py-1.5 rounded-xl bg-white dark:bg-[#0E1524] border border-slate-200 dark:border-slate-700 text-xs font-mono">
            <option value="">Latest Active</option>
            {runs.map(r => <option key={r.id} value={r.id}>{r.id} — {r.target}</option>)}
          </select>
        </div>
      )}
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 dark:from-slate-900 dark:to-black text-white p-6 md:p-8">
        <div className="text-xs font-mono tracking-widest opacity-60">RESEARCH / BENCHMARKS</div>
        <h2 className="text-2xl md:text-3xl font-bold mt-2">Benchmark & Validation Protocol v2.0</h2>
        <p className="text-sm opacity-80 mt-2 max-w-3xl">
          Reproducible, evidence-backed measurements of RakshakX Community Edition. Evaluates discovery, vulnerability identification, evidence quality, verification, reporting, repeatability, and local execution efficiency.
          Primary target: self-hosted fixed-version OWASP Juice Shop. See <span className="font-mono text-xs bg-white/10 px-1.5 py-0.5 rounded">docs/BENCHMARK_V2_PROTOCOL.md</span>.
        </p>
        <div className="mt-4 text-xs opacity-60">Rudraksh AGI · GSTIN 24NKPM5455A1ZX · support@rudrakshai.in · Protocol v2.0</div>
      </div>

      {err && <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-800 p-4 text-sm text-amber-800 dark:text-amber-200">{err}</div>}

      {/* Scorecard */}
      <div className="grid md:grid-cols-4 gap-4">
        {[
          { label: 'Precision', value: scorecard ? scorecard.precision.toFixed(3) : '—', sub: 'TP / (TP+FP)' },
          { label: 'Recall', value: scorecard ? scorecard.recall.toFixed(3) : '—', sub: 'TP / (TP+FN)' },
          { label: 'F1 Score', value: scorecard ? scorecard.f1.toFixed(3) : '—', sub: '2PR/(P+R)' },
          { label: 'Verification Rate', value: scorecard ? scorecard.verification_rate.toFixed(3) : '—', sub: 'Confirmed / candidates' },
        ].map(card => (
          <div key={card.label} className="rounded-2xl bg-white dark:bg-[#0D121F] border border-slate-200 dark:border-slate-800 p-5">
            <div className="text-xs font-semibold tracking-widest text-slate-400">{card.label}</div>
            <div className="text-2xl font-bold mt-1">{card.value}</div>
            <div className="text-xs font-mono text-slate-400 mt-1">{card.sub}</div>
          </div>
        ))}
      </div>

      {scorecard && (
        <div className="rounded-2xl bg-white dark:bg-[#0D121F] border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-bold text-sm">Latest Scorecard</h3>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div><span className="text-slate-400">Scan</span> <span className="font-mono">{scorecard.scan_id}</span></div>
            <div><span className="text-slate-400">Target</span> <span className="font-mono">{scorecard.target}</span></div>
            <div>TP <b className="text-emerald-600">{scorecard.tp}</b> FP <b className="text-red-600">{scorecard.fp}</b> FN <b className="text-amber-600">{scorecard.fn}</b> TN {scorecard.tn}</div>
            <div>Time <b>{scorecard.assessment_time_s.toFixed(2)}s</b></div>
            <div>Ref <b>{scorecard.total_reference}</b> Pred <b>{scorecard.total_predictions}</b></div>
            <div className="col-span-2 md:col-span-3 text-xs font-mono text-slate-500">v{scorecard.protocol_version}</div>
          </div>
        </div>
      )}

      {/* Environment Freeze */}
      {freeze && (
        <div className="rounded-2xl bg-white dark:bg-[#0D121F] border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-bold text-sm">Environment Freeze</h3>
          <div className="mt-3 text-xs font-mono bg-slate-50 dark:bg-slate-900 rounded-xl p-4 overflow-auto max-h-96">
            <div>Hash: <span className="font-bold">{freeze.integrity_hash || '—'}</span></div>
            <div className="mt-2">Python: {(freeze.python?.version || '').split('\n')[0].slice(0,120)}</div>
            <div>OS: {freeze.system?.os_name} {freeze.system?.os_release} {freeze.system?.architecture} · {freeze.system?.hostname}</div>
            <div>Hardware: {freeze.hardware?.cpu_model?.slice(0,80)} · {freeze.hardware?.ram_total_gb}GB RAM · GPU: {freeze.hardware?.gpu_model?.slice(0,60) || 'n/a'}</div>
            <div>Docker: {freeze.docker?.docker_version} API {freeze.docker?.docker_api_version} · Image {freeze.docker?.sandbox_image}</div>
            <div>LLM: {freeze.llm?.model} ({freeze.llm?.provider}) · {freeze.inference}</div>
            <div>Target: {freeze.target?.name} {freeze.target?.version} · {freeze.target?.url_or_ip}</div>
            <div>Prompt: {(freeze.prompt_verbatim || '').slice(0,160)}{(freeze.prompt_verbatim||'').length>160?'…':''}</div>
            <div>Tools: {freeze.security_tools ? Object.entries(freeze.security_tools.tools||freeze.security_tools).slice(0,8).map(([k,v]: any)=> `${k}:${String(v).slice(0,40)}`).join(' | ') : '—'}</div>
          </div>
        </div>
      )}

      {/* Repeatability */}
      {repeat && (
        <div className="rounded-2xl bg-white dark:bg-[#0D121F] border border-slate-200 dark:border-slate-800 p-6">
          <h3 className="font-bold text-sm">Repeatability — 10 Runs (T01 frozen)</h3>
          <div className="mt-3 overflow-auto">
            <table className="w-full text-xs">
              <thead className="text-slate-400">
                <tr><th className="text-left py-2">Run</th><th>Candidates</th><th>TP</th><th>FP</th><th>FN</th><th>Precision</th><th>Recall</th><th>F1</th><th>VR</th><th>Time(s)</th></tr>
              </thead>
              <tbody>
                {(repeat.per_run||[]).map((r:any)=>(
                  <tr key={r.run} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-2 font-mono">{String(r.run).padStart(2,'0')}</td>
                    <td className="text-center">{r.candidate_findings}</td>
                    <td className="text-center font-bold text-emerald-600">{r.tp}</td>
                    <td className="text-center text-red-600">{r.fp}</td>
                    <td className="text-center text-amber-600">{r.fn}</td>
                    <td className="text-center">{Number(r.precision).toFixed(3)}</td>
                    <td className="text-center">{Number(r.recall).toFixed(3)}</td>
                    <td className="text-center">{Number(r.f1).toFixed(3)}</td>
                    <td className="text-center">{Number(r.verification_rate).toFixed(3)}</td>
                    <td className="text-center">{Number(r.assessment_time_s).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {repeat.aggregate && (
            <div className="mt-4 text-xs bg-slate-50 dark:bg-slate-900 rounded-xl p-3">
              Aggregate mean±stdev · P {repeat.aggregate.precision?.mean?.toFixed(3)}±{repeat.aggregate.precision?.stdev?.toFixed(3)} · R {repeat.aggregate.recall?.mean?.toFixed(3)}±{repeat.aggregate.recall?.stdev?.toFixed(3)} · F1 {repeat.aggregate.f1?.mean?.toFixed(3)}±{repeat.aggregate.f1?.stdev?.toFixed(3)}
            </div>
          )}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-amber-50/60 dark:bg-amber-950/20 p-5 text-xs leading-relaxed">
        <div className="font-bold">Integrity Statement</div>
        <div className="mt-1 text-slate-600 dark:text-slate-300">{integrity}</div>
        <div className="mt-3 font-mono text-[11px] text-slate-500">Do not publish a generic accuracy percentage unless the classification task and denominator are rigorously defined.</div>
      </div>

      <div className="text-xs text-slate-400">
        Authorization & Safety: Testing is restricted to intentionally vulnerable self-hosted lab targets or explicitly authorized systems. Keep benchmark environments isolated. Do not test unrelated public systems. Preserve secrets.
      </div>
    </div>
  );
};
