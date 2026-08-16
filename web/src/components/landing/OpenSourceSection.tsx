import React from 'react';
import { Github, BookOpen, GitPullRequest, Star, Terminal, Heart, Scale } from 'lucide-react';

export const OpenSourceSection: React.FC = () => {
  return (
    <section className="py-20 bg-slate-50/50 dark:bg-[#0B0F19]/50 border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 p-8 sm:p-12 shadow-sm text-center space-y-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 text-xs font-semibold border border-brand-200 dark:border-brand-900/60 mx-auto">
            <Star className="w-3.5 h-3.5 fill-brand-500 text-brand-500" />
            <span>COMMUNITY & PHILOSOPHY</span>
          </div>

          <div className="max-w-3xl mx-auto space-y-4">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Built In The Open For Every Engineer
            </h2>
            <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
              <strong>RakshakX (Rakshak AI)</strong> is the open-source & community edition of <strong>Trinetra AI</strong>, designed and architected by <strong>Rudraksh AGI</strong> (Proprietor: <strong>Aditya Kumar Mishra</strong>). Our mission is to make advanced autonomous AI penetration testing accessible, transparent, and reproducible for every engineering team.
            </p>
          </div>

          {/* 4 Feature Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-4xl mx-auto text-xs font-medium">
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 flex items-center justify-center gap-2 text-slate-700 dark:text-slate-300">
              <Star className="w-4 h-4 text-amber-500" />
              <span>100% Open Source</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 flex items-center justify-center gap-2 text-slate-700 dark:text-slate-300">
              <GitPullRequest className="w-4 h-4 text-brand-500" />
              <span>Community Driven</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 flex items-center justify-center gap-2 text-slate-700 dark:text-slate-300">
              <BookOpen className="w-4 h-4 text-sky-500" />
              <span>Fully Documented</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 flex items-center justify-center gap-2 text-slate-700 dark:text-slate-300">
              <Terminal className="w-4 h-4 text-emerald-500" />
              <span>100% Testable & Reproducible</span>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <a
              href="https://github.com/rakshakx/rakshakx"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 shadow-sm transition-all"
            >
              <Github className="w-4 h-4" />
              <span>Star On GitHub</span>
            </a>

            <a
              href="https://github.com/rakshakx/rakshakx/blob/main/CONTRIBUTING.md"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-xs transition-all"
            >
              <GitPullRequest className="w-4 h-4" />
              <span>Contributing Guide</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};
