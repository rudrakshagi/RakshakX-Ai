import React from 'react';
import {
  Eye,
  ArrowRight,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  Network
} from 'lucide-react';

export const ProxySection: React.FC = () => {
  return (
    <section className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <Eye className="w-3.5 h-3.5 text-brand-500" />
            <span>NETWORK OBSERVABILITY</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Transparent Traffic Interception & GraphQL Querying
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            All HTTP and HTTPS traffic emitted by CLI tools, python scripts, and browsers is routed through a local Caido proxy daemon.
          </p>
        </div>

        {/* Traffic Flow Architecture Diagram Card */}
        <div className="rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 p-8 shadow-sm">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-center">
            {/* Step 1: Agent */}
            <div className="p-5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 text-center space-y-2">
              <div className="w-8 h-8 rounded-lg bg-brand-500/10 text-brand-600 dark:text-brand-400 flex items-center justify-center mx-auto font-bold text-xs">
                01
              </div>
              <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">Security Agent</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">Generates fuzzing & dynamic requests</p>
            </div>

            {/* Step 2: Tools / Browser */}
            <div className="p-5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 text-center space-y-2">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center mx-auto font-bold text-xs">
                02
              </div>
              <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">Browser / CLI / Python</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">Executes through system proxy</p>
            </div>

            {/* Step 3: Caido Proxy */}
            <div className="p-5 rounded-xl bg-slate-900 text-white dark:bg-brand-600 border border-slate-900 dark:border-brand-500 text-center space-y-2 shadow-md">
              <div className="w-8 h-8 rounded-lg bg-white/20 text-white flex items-center justify-center mx-auto font-bold text-xs">
                03
              </div>
              <h4 className="font-bold text-sm">Caido Proxy Layer</h4>
              <p className="text-xs text-white/80">GraphQL search & HTTPQL filtering</p>
            </div>

            {/* Step 4: Target */}
            <div className="p-5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 text-center space-y-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto font-bold text-xs">
                04
              </div>
              <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">Target Application</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">Endpoints & API resources</p>
            </div>
          </div>

          {/* GraphQL Feature Callouts */}
          <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-slate-600 dark:text-slate-400">
            <div className="flex items-start gap-2.5">
              <Search className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-900 dark:text-slate-200">HTTPQL Live Querying:</strong>
                <p className="mt-0.5">Agents search requests by status, header tokens, response size, and latency.</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <RefreshCw className="w-4 h-4 text-sky-500 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-900 dark:text-slate-200">Zero-Friction Replay:</strong>
                <p className="mt-0.5">Modify headers or cookies and replay requests directly from the agent reasoning loop.</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-900 dark:text-slate-200">TLS Decryption:</strong>
                <p className="mt-0.5">Private elliptic-curve CA cert trusted by both OS root store and NSS Chromium database.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
