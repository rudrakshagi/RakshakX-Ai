import React from 'react';
import { ArrowRight, Github, Shield, Terminal, CheckCircle2, Play, Sparkles, Globe, Inbox } from 'lucide-react';
import { VulnerabilityFinding } from '../../types';
import { SeverityBadge } from '../common/SeverityBadge';

interface HeroSectionProps {
  onStartScan: () => void;
  onSelectFinding: (finding: VulnerabilityFinding) => void;
  sampleFindings: VulnerabilityFinding[];
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onStartScan,
  onSelectFinding,
  sampleFindings,
}) => {
  const crit = sampleFindings.filter(f => f.severity === 'critical').length;
  const high = sampleFindings.filter(f => f.severity === 'high').length;
  const med = sampleFindings.filter(f => f.severity === 'medium').length;
  const low = sampleFindings.filter(f => f.severity === 'low').length;

  return (
    <section className="relative pt-12 pb-20 md:pt-20 md:pb-28 overflow-hidden">
      {/* Subtle Background Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-brand-500/5 dark:from-brand-500/10 via-transparent to-transparent pointer-events-none blur-3xl -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* LEFT: Headline & Value Proposition */}
          <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
            {/* Pill Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold shadow-xs">
              <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
              <span className="tracking-wide">OPEN-SOURCE AI SECURITY TOOLKIT</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.12]">
              Security Analysis, <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-brand-500 dark:from-brand-500 dark:to-red-400">
                Built For Developers.
              </span>
            </h1>

            {/* Description */}
            <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto lg:mx-0 leading-relaxed font-normal">
              RakshakX combines attack surface reconnaissance, multi-agent AI reasoning, isolated sandbox execution, empirical PoC validation, and compliance-ready reporting into one modular open-source toolkit.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3.5 pt-2">
              <button
                onClick={onStartScan}
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-sm text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 shadow-md shadow-slate-900/10 dark:shadow-brand-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <span>Start A Security Scan</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <a
                href="https://github.com/rakshakx/rakshakx"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 shadow-xs transition-all hover:border-slate-300 dark:hover:border-slate-700"
              >
                <Github className="w-4 h-4" />
                <span>Explore On GitHub</span>
              </a>
            </div>

            {/* Trust Indicators */}
            <div className="pt-6 border-t border-slate-200/80 dark:border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-medium text-slate-600 dark:text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>Open Source (Apache 2.0)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>Modular Multi-Agent</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>0% False Positives (PoC)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span>SARIF 2.1.0 & PDF Ready</span>
              </div>
            </div>
          </div>

          {/* RIGHT: Live Interactive Product Dashboard Mockup */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/90 dark:border-slate-800 shadow-xl shadow-slate-200/50 dark:shadow-black/50 overflow-hidden transition-all">
              {/* Window Header */}
              <div className="px-4 py-3 bg-slate-50/80 dark:bg-[#121B2D] border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-emerald-400" />
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400 ml-2">
                    rakshakx-console · engine_live
                  </span>
                </div>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  sampleFindings.length > 0
                    ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/60'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${sampleFindings.length > 0 ? 'bg-emerald-500 animate-ping' : 'bg-slate-400'}`} />
                  {sampleFindings.length > 0 ? 'Analyzing' : 'Ready'}
                </span>
              </div>

              {/* Scope & Target Bar */}
              <div className="p-4 border-b border-slate-100 dark:border-slate-800/80 bg-white dark:bg-[#0E1524] flex items-center justify-between">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Target Scope
                  </div>
                  <div className="text-sm font-semibold font-mono text-slate-800 dark:text-slate-200 flex items-center gap-1.5 mt-0.5">
                    <Globe className="w-3.5 h-3.5 text-brand-500" />
                    {sampleFindings.length > 0 ? sampleFindings[0].endpoint.split('/')[2] || 'target.app' : 'Awaiting Target Input'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Attack Surface
                  </div>
                  <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 font-mono">
                    {sampleFindings.length > 0 ? '42 Endpoints' : '0 Endpoints'}
                  </div>
                </div>
              </div>

              {/* Metrics Ribbon */}
              <div className="grid grid-cols-4 border-b border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-[#111A2C]/60 text-center py-2.5">
                <div>
                  <div className="text-[10px] uppercase font-bold text-red-500">Crit</div>
                  <div className="text-base font-bold text-red-600 dark:text-red-400">{crit}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-orange-500">High</div>
                  <div className="text-base font-bold text-orange-600 dark:text-orange-400">{high}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-amber-500">Med</div>
                  <div className="text-base font-bold text-amber-600 dark:text-amber-400">{med}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-blue-500">Low</div>
                  <div className="text-base font-bold text-blue-600 dark:text-blue-400">{low}</div>
                </div>
              </div>

              {/* Findings Stream Preview */}
              <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
                {sampleFindings.length === 0 ? (
                  <div className="p-6 text-center space-y-2">
                    <Inbox className="w-6 h-6 text-slate-400 mx-auto" />
                    <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                      No active scan running
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Click "Start A Security Scan" to test your domain or repo.
                    </p>
                  </div>
                ) : (
                  sampleFindings.slice(0, 3).map((f) => (
                    <div
                      key={f.id}
                      onClick={() => onSelectFinding(f)}
                      className="p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100/80 dark:bg-slate-900/60 dark:hover:bg-slate-800/80 border border-slate-200/70 dark:border-slate-800 cursor-pointer transition-all flex items-center justify-between group"
                    >
                      <div className="space-y-1 min-w-0 pr-2">
                        <div className="flex items-center gap-1.5">
                          <SeverityBadge severity={f.severity} score={f.cvss_score} />
                          <span className="text-[10px] font-mono text-slate-400 truncate">
                            {f.cwe_id}
                          </span>
                        </div>
                        <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                          {f.title}
                        </div>
                      </div>
                      <div className="text-[10px] font-mono px-2 py-1 bg-white dark:bg-slate-800 rounded text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 shrink-0">
                        PoC Ready
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Bottom Sandbox Bar */}
              <div className="p-3 bg-slate-50/80 dark:bg-[#121B2D] border-t border-slate-200/80 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span className="flex items-center gap-1.5 font-mono text-[11px]">
                  <Terminal className="w-3.5 h-3.5 text-brand-500" />
                  Kali Linux Sandbox : 48080
                </span>
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  Total Verified: {sampleFindings.length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
