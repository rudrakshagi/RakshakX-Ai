import React from 'react';
import {
  Radar,
  Bug,
  ShieldCheck,
  BrainCircuit,
  SlidersHorizontal,
  FileCheck
} from 'lucide-react';

export const WhatRakshakDoes: React.FC = () => {
  const features = [
    {
      icon: Radar,
      title: 'Attack Surface Discovery',
      description: 'Crawls, spiders, and enumerates endpoints, hidden parameters, and authentication barriers to construct a comprehensive attack surface map.',
      tag: 'Reconnaissance'
    },
    {
      icon: Bug,
      title: 'Dynamic Security Analysis',
      description: 'Executes offensive tools, scripts, and exploit payloads inside an isolated Kali Linux Docker container with zero risk to the host.',
      tag: 'Offensive Probing'
    },
    {
      icon: ShieldCheck,
      title: 'Empirical Evidence Verification',
      description: 'Adheres to the "PoC or it didn\'t happen" standard. Every reported finding includes reproducible verification commands.',
      tag: 'Zero False Positives'
    },
    {
      icon: BrainCircuit,
      title: 'Multi-Agent AI Reasoning',
      description: 'A Root Orchestrator dynamically coordinates specialized subagents (Auth, SQLi, Concurrency) with asynchronous mailbox synchronization.',
      tag: 'Autonomous Red-Team'
    },
    {
      icon: SlidersHorizontal,
      title: 'CVSS 3.1 & Hash Deduplication',
      description: 'Computes exact CVSS 3.1 metric vectors (AV, AC, PR, UI, S, C, I, A) and merges redundant endpoint alerts via composite SHA-256 hashing.',
      tag: 'Risk Scoring'
    },
    {
      icon: FileCheck,
      title: 'Enterprise Compliance Reporting',
      description: 'Generates standard OASIS SARIF 2.1.0 files for GitHub Code Scanning, developer Markdown summaries, and executive PDF assessment reports.',
      tag: 'Reporting'
    }
  ];

  return (
    <section id="features" className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 text-xs font-semibold border border-brand-200 dark:border-brand-900/60">
            <span>CORE CAPABILITIES</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Everything You Need For Autonomous Security Analysis
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            From initial asset discovery to verified proof-of-concept execution and compliance exports.
          </p>
        </div>

        {/* 6-Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, idx) => {
            const Icon = f.icon;
            return (
              <div
                key={idx}
                className="group p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs hover:shadow-xl hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-200 flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="w-11 h-11 rounded-xl bg-slate-100 dark:bg-slate-800 text-brand-600 dark:text-brand-400 flex items-center justify-center group-hover:scale-105 group-hover:bg-brand-50 dark:group-hover:bg-brand-950/50 transition-all">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                      {f.tag}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                    {f.title}
                  </h3>

                  <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
                    {f.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
