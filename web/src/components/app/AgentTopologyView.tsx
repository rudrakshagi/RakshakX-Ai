import React, { useState, useEffect } from 'react';
import { INITIAL_AGENTS } from '../../data/mockScanData';
import { Network, Cpu, Mail, Send, CheckCircle2, Clock, Sparkles, HeartPulse, AlertTriangle } from 'lucide-react';
import { AgentNode } from '../../types';

type HealthVerdict = 'running' | 'waiting' | 'idle' | 'degraded' | 'stuck_suspected' | 'stopped' | 'finished' | 'paused' | 'unknown';

interface AgentHealth {
  id: string;
  verdict: HealthVerdict;
  detail: string;
  seconds_since_heartbeat: number | null;
}

const VERDICT_STYLE: Record<HealthVerdict, { dot: string; pill: string; label: string }> = {
  running: { dot: 'bg-emerald-500 animate-pulse', pill: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-900', label: 'Running' },
  waiting: { dot: 'bg-blue-500', pill: 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-900', label: 'Waiting' },
  idle: { dot: 'bg-amber-400 animate-pulse', pill: 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-900', label: 'Idle 60s+' },
  degraded: { dot: 'bg-amber-500 animate-pulse', pill: 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-900', label: 'Degraded' },
  stuck_suspected: { dot: 'bg-orange-500 animate-ping', pill: 'bg-orange-50 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-900', label: 'Stuck?' },
  stopped: { dot: 'bg-red-500', pill: 'bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border-red-200 dark:border-red-900', label: 'Stopped' },
  finished: { dot: 'bg-slate-400', pill: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700', label: 'Finished' },
  paused: { dot: 'bg-violet-500', pill: 'bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 border-violet-200 dark:border-violet-900', label: 'Paused' },
  unknown: { dot: 'bg-slate-300', pill: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700', label: 'Unknown' },
};

export const AgentTopologyView: React.FC<{ liveAgents?: AgentNode[]; onStartScan?: () => void }> = ({ liveAgents, onStartScan }) => {
  const [agents, setAgents] = useState<AgentNode[]>(liveAgents ?? []);
  const [steerMsg, setSteerMsg] = useState('');
  const [sentFeedback, setSentFeedback] = useState(false);
  // 5-second watchdog: liveness verdicts per agent (stuck / stopped detection)
  const [health, setHealth] = useState<Record<string, AgentHealth>>({});
  const [watchdogOk, setWatchdogOk] = useState(true);

  // If parent provides liveAgents, sync from it directly
  useEffect(() => {
    if (liveAgents !== undefined) {
      setAgents(liveAgents);
    }
  }, [liveAgents]);

  useEffect(() => {
    if (liveAgents !== undefined) return; // parent handles live state
    let cancelled = false;
    async function loadAgents() {
      try {
        const res = await fetch('/api/agents');
        if (!res.ok) return;
        const data = await res.json();
        const names = data.names || {};
        if (cancelled) return;

        if (Object.keys(names).length === 0) {
          setAgents([]);
          return;
        }

        const statuses = data.statuses || {};
        const meta = data.metadata || {};
        setAgents(Object.keys(names).map(aid => ({
          id: aid,
          name: names[aid],
          role: aid === 'root_01' || aid === 'agent-root' ? 'Scope & Task Dispatcher' : 'Specialist Subagent',
          status: (statuses[aid] || 'running').toLowerCase() as AgentNode['status'],
          task: meta[aid]?.task || 'Autonomous reconnaissance and probing.',
          parentId: data.parent_of?.[aid] || null,
          messagesCount: meta[aid]?.pending_counts ?? 0,
          skills: meta[aid]?.skills || ['offensive_playbook'],
        })));
      } catch (e) {
        if (!cancelled) setAgents([]);
      }
    }
    loadAgents();
    const interval = setInterval(loadAgents, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [liveAgents]);

  // 5-second watchdog — runs regardless of liveAgents source, polls liveness verdicts
  useEffect(() => {
    let cancelled = false;
    async function checkHealth() {
      try {
        const res = await fetch('/api/agents/health');
        if (!res.ok) throw new Error(`health ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        const map: Record<string, AgentHealth> = {};
        for (const a of data.agents || []) {
          map[a.id] = {
            id: a.id,
            verdict: a.verdict as HealthVerdict,
            detail: a.detail || '',
            seconds_since_heartbeat: a.seconds_since_heartbeat ?? null,
          };
        }
        setHealth(map);
        setWatchdogOk(true);
      } catch {
        if (!cancelled) setWatchdogOk(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const attentionAgents = agents.filter(a => {
    const v = health[a.id]?.verdict;
    return v === 'stuck_suspected' || v === 'stopped' || v === 'degraded';
  });

  const idleAgents = agents.filter(a => health[a.id]?.verdict === 'idle');

  const handleSendSteer = (e: React.FormEvent) => {    e.preventDefault();
    if (!steerMsg.trim()) return;

    fetch('/api/steer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instruction: steerMsg.trim() }),
    }).catch(() => {});

    setSentFeedback(true);
    setSteerMsg('');
    setTimeout(() => setSentFeedback(false), 3000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Description Card */}
      <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Active Multi-Agent Topology
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time process status, async mailboxes, and cognitive task assignments.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${agents.length > 0 ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
          <span className="text-xs font-semibold font-mono text-slate-600 dark:text-slate-300">
            {agents.length > 0 ? `${agents.length} Active Processes` : '0 Active Processes'}
          </span>
        </div>
      </div>

      {/* Watchdog attention banner */}
      {attentionAgents.length > 0 && (
        <div className="p-4 rounded-2xl bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-900/50 flex items-start gap-2.5 shadow-xs animate-fadeIn">
          <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400 shrink-0 mt-0.5" />
          <div className="text-xs text-orange-800 dark:text-orange-300 leading-relaxed">
            <span className="font-bold">Watchdog (5s): {attentionAgents.length} agent{attentionAgents.length > 1 ? 's need' : ' needs'} attention — </span>
            {attentionAgents.map(a => `${a.name} (${VERDICT_STYLE[health[a.id]?.verdict ?? 'unknown'].label})`).join(', ')}. Check details on the card or steer the agent below.
          </div>
        </div>
      )}
      {attentionAgents.length === 0 && idleAgents.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 flex items-start gap-2.5 shadow-xs">
          <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
            <span className="font-bold">Slowing (60s+ no heartbeat): </span>
            {idleAgents.map(a => `${a.name} (${health[a.id]?.detail ?? 'idle'})`).join(', ')}. Still below the 180s stuck threshold — keep an eye, no action needed yet.
          </div>
        </div>
      )}
      {!watchdogOk && agents.length > 0 && (
        <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <HeartPulse className="w-3.5 h-3.5" />
          <span>Watchdog unreachable — showing last known status. Backend /api/agents/health may be down.</span>
        </div>
      )}

      {/* Agents Grid or Empty State */}
      {agents.length === 0 ? (
        <div className="p-12 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-slate-100 dark:bg-slate-800/80 text-slate-400 dark:text-slate-500 flex items-center justify-center mx-auto">
            <Cpu className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              No Active Agents Running
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1">
              The multi-agent execution topology is currently idle. Launch an offensive scan or start an AI Security session to spawn autonomous agents in real time.
            </p>
          </div>
          {onStartScan && (
            <button
              onClick={onStartScan}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 transition-colors shadow-xs"
            >
              <Sparkles className="w-4 h-4" />
              <span>Launch New Scan</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 flex items-center justify-center font-mono text-xs font-bold">
                      <Cpu className="w-4 h-4" />
                    </div>
                    <span className="font-bold text-sm text-slate-900 dark:text-slate-100">
                      {agent.name}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full ${
                      agent.status === 'running'
                        ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900'
                        : 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-900'
                    }`}
                  >
                    {agent.status}
                  </span>
                </div>

                {/* Watchdog liveness badge */}
                {(() => {
                  const h = health[agent.id];
                  const style = VERDICT_STYLE[h?.verdict ?? 'unknown'];
                  return (
                    <div className="flex items-center gap-1.5" title={h?.detail || 'No watchdog data yet'}>
                      <span className={`w-2 h-2 rounded-full ${style.dot}`} />
                      <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full border ${style.pill}`}>
                        {style.label}
                      </span>
                      {h?.seconds_since_heartbeat != null && (
                        <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                          turn {h.seconds_since_heartbeat}s ago
                        </span>
                      )}
                      {!watchdogOk && (
                        <span className="text-[10px] font-mono text-slate-400">(stale)</span>
                      )}
                    </div>
                  );
                })()}

                <div className="text-xs font-semibold text-brand-600 dark:text-brand-400">
                  Role: {agent.role}
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {agent.task}
                </p>

                <div className="space-y-1.5 pt-2">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Assigned Skills
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {agent.skills.map((s, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-600 dark:text-slate-300"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Mailbox: {agent.messagesCount} msgs</span>
                <span>PID: {agent.id}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Live Steering Form Card */}
      <div className="p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs space-y-4">
        <div>
          <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Mail className="w-4 h-4 text-brand-500" />
            Human-in-the-Loop Agent Steering Mailbox
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Deliver real-time high-priority instructions into the Root Orchestrator's mailbox mid-scan.
          </p>
        </div>

        <form onSubmit={handleSendSteer} className="flex gap-3">
          <input
            type="text"
            value={steerMsg}
            onChange={(e) => setSteerMsg(e.target.value)}
            placeholder="e.g. Focus probing specifically on /api/v1/auth/jwt and skip DNS bruteforce..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500"
          />
          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 transition-colors flex items-center gap-1.5 shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send Instruction</span>
          </button>
        </form>

        {sentFeedback && (
          <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Instruction deposited in Root Orchestrator mailbox. Agent will prioritize next turn.</span>
          </div>
        )}
      </div>
    </div>
  );
};
