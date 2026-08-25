import React, { useState, useEffect } from 'react';
import { INITIAL_AGENTS } from '../../data/mockScanData';
import { Network, Cpu, Mail, Send, CheckCircle2, Clock, Sparkles } from 'lucide-react';
import { AgentNode } from '../../types';

export const AgentTopologyView: React.FC = () => {
  const [agents, setAgents] = useState<AgentNode[]>(INITIAL_AGENTS);
  const [steerMsg, setSteerMsg] = useState('');
  const [sentFeedback, setSentFeedback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadAgents() {
      try {
        const res = await fetch('/api/agents');
        if (!res.ok) return;
        const data = await res.json();
        const names = data.names || {};
        if (Object.keys(names).length === 0 || cancelled) return;
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
          skills: ['offensive_playbook'],
        })));
      } catch (e) {
        // Backend offline, keep mock
      }
    }
    loadAgents();
    const interval = setInterval(loadAgents, 2000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const handleSendSteer = (e: React.FormEvent) => {
    e.preventDefault();
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
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold font-mono text-emerald-600 dark:text-emerald-400">
            Zero Deadlock Engine
          </span>
        </div>
      </div>

      {/* Agents Grid */}
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
