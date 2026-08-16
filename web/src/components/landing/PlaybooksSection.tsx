import React, { useState } from 'react';
import { PLAYBOOKS_CATALOG } from '../../data/playbooksData';
import { BookOpen, Key, Database, ShieldAlert, Cpu, Sparkles, Check, FileText } from 'lucide-react';
import { PlaybookItem } from '../../types';

export const PlaybooksSection: React.FC = () => {
  const [selectedPlaybook, setSelectedPlaybook] = useState<PlaybookItem>(PLAYBOOKS_CATALOG[0]);
  const [loadedSkills, setLoadedSkills] = useState<Record<string, boolean>>({});

  const handleToggleLoad = (id: string) => {
    setLoadedSkills(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <section id="playbooks" className="py-20 bg-white dark:bg-[#090D16] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <BookOpen className="w-3.5 h-3.5 text-brand-500" />
            <span>MODULAR OFFENSIVE METHODOLOGY</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Curated Security Skills & Exploit Playbooks
          </h2>
          <p className="text-base text-slate-600 dark:text-slate-400">
            Subagents dynamically load specialized domain knowledge into their active reasoning context via the <code>load_skill()</code> tool.
          </p>
        </div>

        {/* Playbook Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {PLAYBOOKS_CATALOG.map((p) => {
            const isLoaded = loadedSkills[p.id];
            return (
              <div
                key={p.id}
                onClick={() => setSelectedPlaybook(p)}
                className={`p-6 rounded-2xl bg-slate-50 dark:bg-[#0E1524] border transition-all duration-200 cursor-pointer flex flex-col justify-between ${
                  selectedPlaybook.id === p.id
                    ? 'border-brand-500 shadow-md shadow-brand-500/10'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950/40 px-2.5 py-1 rounded border border-brand-200 dark:border-brand-900/60 font-semibold">
                      {p.filename}
                    </span>
                    <span className="text-[10px] font-mono uppercase font-bold text-slate-400">
                      {p.category}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    {p.name}
                  </h3>

                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {p.description}
                  </p>

                  <div className="space-y-1.5 pt-2">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                      Target Vectors Covered
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {p.attackVectors.map((v, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded bg-white dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-[11px] font-mono text-slate-700 dark:text-slate-300"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-200/80 dark:border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-mono">
                    Status: <span className="text-emerald-500 font-bold">Ready</span>
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleLoad(p.id);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                      isLoaded
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white'
                    }`}
                  >
                    {isLoaded ? <Check className="w-3.5 h-3.5" /> : <Cpu className="w-3.5 h-3.5" />}
                    <span>{isLoaded ? 'Skill Loaded' : 'Load Skill'}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
