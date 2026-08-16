import React, { useState } from 'react';
import {
  Network,
  Cpu,
  Mail,
  Shield,
  KeyRound,
  Database,
  Timer,
  Zap,
  Globe2,
  CheckCircle2,
  ChevronRight
} from 'lucide-react';

export const ArchitectureGraph: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<'root' | 'recon' | 'auth' | 'sqli' | 'race'>('root');

  const agentDetails = {
    root: {
      title: 'Root Orchestrator',
      role: 'Scope Mapping & Tactical Delegation',
      description: 'The master cognitive loop. Analyzes target domains or repositories, establishes attack surfaces, creates specialized task definitions, and dispatches child agents.',
      tools: ['Session Manager', 'Scope Analyzer', 'Agent Coordinator', 'Executive Reporter'],
      mailboxStatus: 'Active (3 Subagents Connected)',
      codeSample: `// Root Orchestrator dispatches specialists
await create_agent("Auth Specialist", {
  task: "Probe /api/v1/auth for JWT algorithm confusion & none alg",
  skills: ["authentication_jwt"]
});
await wait_for_agents();`
    },
    recon: {
      title: 'Reconnaissance Agent',
      role: 'Surface Discovery & Spidering',
      description: 'Discovers endpoints, parameters, hidden directories, technologies, and authentication entry points via Katana, FFuF, and Nmap.',
      tools: ['Katana Spider', 'FFuF Fuzzer', 'Httpx', 'Nmap Port Scanner'],
      mailboxStatus: 'Completed (42 Endpoints Discovered)',
      codeSample: `// Katana spidering across target
katana -u https://example.com -d 3 -jc -proxy http://127.0.0.1:48080`
    },
    auth: {
      title: 'Authentication Specialist',
      role: 'Token Security & Privilege Escalation',
      description: 'Specializes in JWT algorithm confusion (RS256 to HS256), none alg attacks, key ID traversal, and OAuth session fixation.',
      tools: ['jwt_tool', 'Caido Proxy API', 'Public Key Extractor'],
      mailboxStatus: 'Completed (1 Critical Finding Verified)',
      codeSample: `// Exploiting JWT algorithm confusion in sandbox
jwt_tool $TOKEN -X k -pk /workspace/public.pem
curl -i -H "Authorization: Bearer $FORGED" https://example.com/api/admin`
    },
    sqli: {
      title: 'SQLi Specialist',
      role: 'Database Injection & Data Probing',
      description: 'Probes parameters with boolean blind, time-delay sleep vectors, and automated SQLmap proxy extraction to confirm database access.',
      tools: ['Sqlmap', 'Custom Sleep Payloads', 'Caido Query Replayer'],
      mailboxStatus: 'Completed (1 High Finding Verified)',
      codeSample: `// Blind time-based PostgreSQL sleep probe
curl -s "https://example.com/api/search?q=test'%20OR%20pg_sleep(5)--%20-"`
    },
    race: {
      title: 'Concurrency Specialist',
      role: 'Business Logic & Race Conditions',
      description: 'Executes parallel HTTP/2 single-packet burst attacks to test promo code double-redemptions, balance double-spends, and IDORs.',
      tools: ['HTTP/2 Burst Engine', 'Asyncio Flood Scripts'],
      mailboxStatus: 'Running (20 Burst Requests Sent)',
      codeSample: `// Concurrent burst redemption
async with httpx.AsyncClient(http2=True) as client:
    tasks = [client.post(REDEEM_URL, json=CODE) for _ in range(20)]
    results = await asyncio.gather(*tasks)`
    }
  };

  const current = agentDetails[selectedAgent];

  return (
    <section id="architecture" className="py-20 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <Network className="w-3.5 h-3.5 text-brand-500" />
            <span>MULTI-AGENT TOPOLOGY</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            From One Target To A Complete Security Analysis
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            A resilient, event-driven multi-agent hierarchy coordinating specialized offensive roles with zero CPU deadlocks.
          </p>
        </div>

        {/* Interactive Architecture Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left: Interactive Node Tree Visualizer */}
          <div className="lg:col-span-7 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-6 flex items-center justify-between">
              <span>Interactive Agent Graph (Click any node)</span>
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Async Mailboxes Ready
              </span>
            </div>

            {/* Root Node */}
            <div className="flex flex-col items-center">
              <div
                onClick={() => setSelectedAgent('root')}
                className={`w-full max-w-md p-4 rounded-xl cursor-pointer transition-all border flex items-center justify-between ${
                  selectedAgent === 'root'
                    ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-md'
                    : 'bg-white dark:bg-[#121B2D] text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-brand-500/20 text-brand-500">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-bold text-sm">Root Orchestrator</div>
                    <div className="text-xs opacity-80">Scope Mapping & Coordinator</div>
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/20 dark:bg-black/40 text-white">
                  PID #01
                </span>
              </div>

              {/* Connecting Trunk Line */}
              <div className="w-0.5 h-8 bg-slate-300 dark:bg-slate-700 my-1" />

              {/* Branch Bar */}
              <div className="w-full max-w-lg h-0.5 bg-slate-300 dark:bg-slate-700 mb-4 relative">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-brand-500" />
              </div>

              {/* Child Specialist Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
                {/* Recon */}
                <div
                  onClick={() => setSelectedAgent('recon')}
                  className={`p-3 rounded-xl cursor-pointer border text-center transition-all ${
                    selectedAgent === 'recon'
                      ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-md'
                      : 'bg-white dark:bg-[#121B2D] text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-700 hover:border-slate-400'
                  }`}
                >
                  <Globe2 className="w-4 h-4 mx-auto mb-1 text-sky-500" />
                  <div className="text-xs font-bold truncate">Recon & Surface</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">42 Endpoints</div>
                </div>

                {/* Auth */}
                <div
                  onClick={() => setSelectedAgent('auth')}
                  className={`p-3 rounded-xl cursor-pointer border text-center transition-all ${
                    selectedAgent === 'auth'
                      ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-md'
                      : 'bg-white dark:bg-[#121B2D] text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-700 hover:border-slate-400'
                  }`}
                >
                  <KeyRound className="w-4 h-4 mx-auto mb-1 text-amber-500" />
                  <div className="text-xs font-bold truncate">Auth Specialist</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">JWT / OAuth</div>
                </div>

                {/* SQLi */}
                <div
                  onClick={() => setSelectedAgent('sqli')}
                  className={`p-3 rounded-xl cursor-pointer border text-center transition-all ${
                    selectedAgent === 'sqli'
                      ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-md'
                      : 'bg-white dark:bg-[#121B2D] text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-700 hover:border-slate-400'
                  }`}
                >
                  <Database className="w-4 h-4 mx-auto mb-1 text-emerald-500" />
                  <div className="text-xs font-bold truncate">SQLi Prober</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">Database Injection</div>
                </div>

                {/* Concurrency */}
                <div
                  onClick={() => setSelectedAgent('race')}
                  className={`p-3 rounded-xl cursor-pointer border text-center transition-all ${
                    selectedAgent === 'race'
                      ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-md'
                      : 'bg-white dark:bg-[#121B2D] text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-700 hover:border-slate-400'
                  }`}
                >
                  <Timer className="w-4 h-4 mx-auto mb-1 text-purple-500" />
                  <div className="text-xs font-bold truncate">Concurrency</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate">Race Conditions</div>
                </div>
              </div>

              {/* Mailbox sync caption */}
              <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 w-full flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span className="flex items-center gap-1.5 font-mono text-[11px]">
                  <Mail className="w-3.5 h-3.5 text-brand-500" />
                  send_message_to_agent() · wait_for_agents()
                </span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                  Zero Deadlock Coordination
                </span>
              </div>
            </div>
          </div>

          {/* Right: Node Detail Panel */}
          <div className="lg:col-span-5 space-y-4">
            <div className="p-6 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    {current.title}
                  </h3>
                  <p className="text-xs text-brand-600 dark:text-brand-400 font-medium">
                    {current.role}
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/60">
                  {current.mailboxStatus}
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {current.description}
              </p>

              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
                  Assigned Tools & Skillsets
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {current.tools.map((t, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-700 dark:text-slate-300"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
                  Subagent Sandbox Execution Trace
                </div>
                <div className="p-3.5 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto border border-slate-800">
                  <pre className="text-sky-400 leading-relaxed">{current.codeSample}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
