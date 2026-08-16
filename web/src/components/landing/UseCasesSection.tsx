import React from 'react';
import {
  Globe,
  Code2,
  Zap,
  GitPullRequest,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';

export const UseCasesSection: React.FC = () => {
  const useCases = [
    {
      title: 'Black-Box Web Penetration Testing',
      tag: 'Dynamic Assessment',
      icon: Globe,
      input: 'https://example.com',
      steps: [
        'Passive & active reconnaissance via Katana',
        'Parameter extraction & attack surface mapping',
        'Autonomous multi-agent exploit probing',
        'Empirical PoC generation & verification',
        'Compliance SARIF & PDF report generation'
      ]
    },
    {
      title: 'White-Box Source Code Audit',
      tag: 'Static & Tainted Flow',
      icon: Code2,
      input: '/project/backend (Local Git Repo)',
      steps: [
        'AST parsing with Tree-Sitter & Semgrep',
        'Tainted data flow & injection source tracing',
        'Dangerous function & hardcoded secret detection',
        'Local sandbox environment reproduction',
        'Source line & code patch diff generation'
      ]
    },
    {
      title: 'Business Logic & Concurrency Testing',
      tag: 'Deep Logic Probing',
      icon: Zap,
      input: 'Stateful Multi-step Workflows',
      steps: [
        'Multi-user tenant boundary verification (IDOR)',
        'Parallel HTTP/2 single-packet burst testing',
        'Promo code & gift card double-redemption',
        'Balance race conditions & negative amounts',
        'Database transaction lock validation'
      ]
    },
    {
      title: 'DevSecOps & Automated CI/CD Blocking',
      tag: 'Continuous Security',
      icon: GitPullRequest,
      input: 'GitHub Pull Request / GitLab MR',
      steps: [
        'Ephemeral container triggered on git push',
        'Incremental scan on modified routes & APIs',
        'Direct SARIF 2.1.0 annotation on GitHub PR',
        'Blocks merge if Critical / High finding verified',
        'Zero false positive developer friction'
      ]
    }
  ];

  return (
    <section id="use-cases" className="py-20 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <Globe className="w-3.5 h-3.5 text-brand-500" />
            <span>VERSATILE WORKFLOWS</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Built For Every Modern Security Workflow
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            Deploy RakshakX across black-box web audits, source code repositories, and automated CI/CD gating.
          </p>
        </div>

        {/* 4 Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {useCases.map((u, idx) => {
            const Icon = u.icon;
            return (
              <div
                key={idx}
                className="p-7 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border border-slate-200 dark:border-slate-800 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all space-y-5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 flex items-center justify-center text-brand-600 dark:text-brand-400">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-base text-slate-900 dark:text-slate-100">
                        {u.title}
                      </h3>
                      <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                        {u.tag}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-white dark:bg-[#121B2D] rounded-xl border border-slate-200 dark:border-slate-700/80 font-mono text-xs text-slate-700 dark:text-sky-400 flex items-center justify-between">
                  <span>Input: {u.input}</span>
                  <span className="text-[10px] text-slate-400 font-sans">Target Input</span>
                </div>

                <div className="space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Execution Lifecycle
                  </div>
                  <div className="space-y-2">
                    {u.steps.map((step, sIdx) => (
                      <div key={sIdx} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
