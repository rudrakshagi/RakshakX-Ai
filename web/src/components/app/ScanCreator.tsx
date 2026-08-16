import React, { useState } from 'react';
import { Play, Globe, Code2, ShieldAlert, CheckSquare, Square, Terminal, CheckCircle2, ArrowRight, Sparkles } from 'lucide-react';

interface ScanCreatorProps {
  onScanLaunched: (target: string, mode: string) => void;
}

export const ScanCreator: React.FC<ScanCreatorProps> = ({ onScanLaunched }) => {
  const [targetType, setTargetType] = useState<'domain' | 'url' | 'repo'>('domain');
  const [targetValue, setTargetValue] = useState('example.com');
  const [scanMode, setScanMode] = useState<'blackbox' | 'whitebox'>('blackbox');
  const [customPrompt, setCustomPrompt] = useState('');
  const [authorized, setAuthorized] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState('');

  const [modules, setModules] = useState({
    recon: true,
    http: true,
    dns: true,
    tls: true,
    tech: true,
    vuln: true,
    poc: true,
  });

  const toggleModule = (key: keyof typeof modules) => {
    setModules(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleLaunch = () => {
    if (!targetValue || !authorized) return;
    setIsScanning(true);
    setScanStep('Initializing isolated Kali Linux Docker container...');

    fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: targetValue,
        mode: scanMode === 'blackbox' ? 'Black Box' : 'White Box',
        prompt: customPrompt,
      }),
    }).catch(() => {});

    setTimeout(() => {
      setScanStep('Starting transparent Caido proxy daemon on port 48080...');
    }, 800);

    setTimeout(() => {
      setScanStep('Dispatching Root Orchestrator and Recon Specialist with AI directives...');
    }, 1600);

    setTimeout(() => {
      setIsScanning(false);
      onScanLaunched(targetValue, scanMode === 'blackbox' ? 'Black Box' : 'White Box');
    }, 2400);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="p-8 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-8">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 text-xs font-semibold border border-brand-200 dark:border-brand-900/60 mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AUTONOMOUS AGENT DISPATCH</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Launch New Security Assessment
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Configure target parameters, assessment mode, and custom natural language AI directives.
          </p>
        </div>

        {/* Form Fields */}
        <div className="space-y-6">
          {/* Target Type Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Target Scope Type
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'domain', label: 'Domain Name', desc: 'example.com' },
                { id: 'url', label: 'Full Web URL', desc: 'https://api.app.com' },
                { id: 'repo', label: 'Source Repository', desc: '/path/to/code' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTargetType(t.id as any)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    targetType === t.id
                      ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-xs'
                      : 'bg-slate-50 dark:bg-[#121B2D] text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700'
                  }`}
                >
                  <div className="font-bold text-xs">{t.label}</div>
                  <div className="text-[10px] opacity-70 font-mono mt-0.5">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Target Input */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Target Input
            </label>
            <input
              type="text"
              value={targetValue}
              onChange={(e) => setTargetValue(e.target.value)}
              placeholder="e.g. example.com or https://api.target.com"
              className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 font-mono text-sm text-slate-900 dark:text-slate-100 focus:outline-hidden focus:border-brand-500"
            />
          </div>

          {/* Natural Language AI Directives & Scope Input */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Custom AI Directives & Security Focus (Natural Language)
            </label>
            <div className="relative">
              <textarea
                rows={3}
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="e.g. Focus specifically on /api/v1/auth and /api/v1/checkout. Test for JWT signature confusion, coupon race conditions, and IDOR on user profiles. Exclude /logout endpoint..."
                className="w-full p-4 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500 resize-none font-mono leading-relaxed"
              />
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
              The Root Orchestrator AI will parse this prompt into prioritized subtasks for specialized child agents.
            </p>
          </div>

          {/* Scan Mode Toggle */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Assessment Mode
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setScanMode('blackbox')}
                className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3 ${
                  scanMode === 'blackbox'
                    ? 'bg-brand-50/50 dark:bg-brand-950/20 border-brand-500 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'bg-slate-50 dark:bg-[#121B2D] border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                }`}
              >
                <Globe className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-xs">Black Box Dynamic Assessment</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Simulates real-world external penetration testing with no source access.
                  </div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setScanMode('whitebox')}
                className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3 ${
                  scanMode === 'whitebox'
                    ? 'bg-brand-50/50 dark:bg-brand-950/20 border-brand-500 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'bg-slate-50 dark:bg-[#121B2D] border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                }`}
              >
                <Code2 className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-xs">White Box Source Code Audit</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    AST taint analysis, Semgrep rules & local sandbox reproduction.
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Module Toggles */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Reconnaissance & Probing Modules
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { id: 'recon', label: 'Reconnaissance' },
                { id: 'http', label: 'HTTP Analysis' },
                { id: 'dns', label: 'DNS Analysis' },
                { id: 'tls', label: 'TLS / SSL Analysis' },
                { id: 'tech', label: 'Tech Stack Fingerprinting' },
                { id: 'vuln', label: 'Vulnerability Probing' },
                { id: 'poc', label: 'Empirical PoC Verification' },
              ].map((m) => {
                const isChecked = modules[m.id as keyof typeof modules];
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleModule(m.id as any)}
                    className={`p-2.5 rounded-lg border text-left text-xs font-medium flex items-center justify-between transition-colors ${
                      isChecked
                        ? 'bg-slate-900 text-white dark:bg-slate-800 dark:text-white border-slate-800'
                        : 'bg-slate-50 dark:bg-[#121B2D] text-slate-500 border-slate-200 dark:border-slate-700'
                    }`}
                  >
                    <span className="truncate">{m.label}</span>
                    {isChecked ? (
                      <CheckSquare className="w-3.5 h-3.5 text-brand-400 shrink-0 ml-1" />
                    ) : (
                      <Square className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Authorization Checkbox */}
          <div
            onClick={() => setAuthorized(!authorized)}
            className="p-4 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 flex items-center gap-3 cursor-pointer select-none"
          >
            {authorized ? (
              <CheckSquare className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0" />
            ) : (
              <Square className="w-4 h-4 text-slate-400 shrink-0" />
            )}
            <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
              I confirm that I am explicitly authorized to test this target application or domain.
            </span>
          </div>

          {/* Launch Status / Button */}
          {isScanning ? (
            <div className="p-4 rounded-xl bg-slate-900 text-white font-mono text-xs space-y-2 border border-slate-800">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span>SPAWNING SANDBOX RUNTIME</span>
              </div>
              <div className="text-slate-300">{scanStep}</div>
            </div>
          ) : (
            <button
              onClick={handleLaunch}
              disabled={!targetValue || !authorized}
              className="w-full py-4 rounded-xl font-bold text-sm text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-md shadow-brand-600/10"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Start Autonomous Security Scan</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
