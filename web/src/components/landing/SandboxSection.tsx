import React from 'react';
import {
  Box,
  Terminal,
  Shield,
  Search,
  Zap,
  Database,
  Globe,
  Code2,
  Lock
} from 'lucide-react';

export const SandboxSection: React.FC = () => {
  const tools = [
    {
      name: 'Nmap',
      category: 'Network & Ports',
      desc: 'Port discovery and service version fingerprinting inside container sandbox.',
      icon: Search
    },
    {
      name: 'Nuclei',
      category: 'Vulnerability Templates',
      desc: 'High-speed template-based scanning for known CVEs and misconfigurations.',
      icon: Zap
    },
    {
      name: 'SQLMap',
      category: 'Database Injection',
      desc: 'Automated database takeover and blind time-delay query exploitation.',
      icon: Database
    },
    {
      name: 'FFuF & Katana',
      category: 'Web Fuzzing & Spidering',
      desc: 'Rapid parameter discovery, hidden endpoint bruteforcing, and JS crawling.',
      icon: Globe
    },
    {
      name: 'Semgrep & Tree-Sitter',
      category: 'Whitebox AST Analysis',
      desc: 'Abstract syntax tree parsing for tainted data flow and dangerous functions.',
      icon: Code2
    },
    {
      name: 'Agent Browser',
      category: 'DOM & Client-Side',
      desc: 'Headless Chromium browser automation with stealth flags & screenshot capture.',
      icon: Terminal
    }
  ];

  return (
    <section id="sandbox" className="py-20 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Description */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
              <Box className="w-3.5 h-3.5 text-brand-500" />
              <span>ISOLATED KALI LINUX RUNTIME</span>
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight">
              Security Analysis Inside An Isolated Environment
            </h2>

            <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed">
              Every assessment executes inside a dedicated, containerized Kali Linux sandbox. Dynamic scripts, browser sessions, and exploit payloads are strictly isolated from the host machine.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex items-start gap-3">
                <div className="p-1 rounded bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 mt-0.5">
                  <Shield className="w-4 h-4" />
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                  <strong>Zero Host Contamination:</strong> Ephemeral bind mounts and auto-cleanup destroy container state post-scan.
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-1 rounded bg-sky-50 dark:bg-sky-950 text-sky-600 dark:text-sky-400 mt-0.5">
                  <Lock className="w-4 h-4" />
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                  <strong>Transparent Proxy Redirection:</strong> System-wide environment variables force all tool traffic through Caido.
                </div>
              </div>
            </div>
          </div>

          {/* Right: Modern Tool Cards Grid */}
          <div className="lg:col-span-7">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {tools.map((t, idx) => {
                const Icon = t.icon;
                return (
                  <div
                    key={idx}
                    className="p-5 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all space-y-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 flex items-center justify-center text-brand-600 dark:text-brand-400">
                          <Icon className="w-4 h-4" />
                        </div>
                        <span className="font-bold text-sm text-slate-900 dark:text-slate-100">
                          {t.name}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">
                        Sandbox Exec
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                      {t.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
