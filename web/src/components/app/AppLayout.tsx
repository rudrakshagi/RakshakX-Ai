import React from 'react';
import {
  Shield,
  LayoutDashboard,
  PlusCircle,
  Bug,
  Network,
  BookOpen,
  FileCheck,
  Settings,
  ArrowLeft,
  Key,
  Bot
} from 'lucide-react';
import { ThemeToggle } from '../common/ThemeToggle';
import { Logo } from '../common/Logo';
import { SocialFooterStrip } from '../common/SocialFooterStrip';

export type AppTab = 'overview' | 'new-scan' | 'findings' | 'agents' | 'playbooks' | 'reports' | 'settings' | 'ai-chat';

interface AppLayoutProps {
  currentTab: AppTab;
  setCurrentTab: (tab: AppTab) => void;
  onBackToLanding: () => void;
  darkMode: boolean;
  setDarkMode: (val: boolean) => void;
  children: React.ReactNode;
  verifiedFindingsCount: number;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentTab,
  setCurrentTab,
  onBackToLanding,
  darkMode,
  setDarkMode,
  children,
  verifiedFindingsCount
}) => {
  const navItems: { id: AppTab; label: string; icon: React.FC<{ className?: string }>; count?: number }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'new-scan', label: 'New Scan', icon: PlusCircle },
    { id: 'findings', label: 'Findings Ledger', icon: Bug, count: verifiedFindingsCount },
    { id: 'agents', label: 'Agent Topology', icon: Network },
    { id: 'ai-chat', label: 'AI Security Chat', icon: Bot },
    { id: 'playbooks', label: 'Playbooks & Skills', icon: BookOpen },
    { id: 'reports', label: 'Compliance Reports', icon: FileCheck },
    { id: 'settings', label: 'LLM & API Settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#FAFAFA] dark:bg-[#090D16] text-slate-900 dark:text-slate-100 transition-colors">
      {/* Sidebar */}
      <aside className="w-64 bg-white dark:bg-[#0D121F] border-r border-slate-200/80 dark:border-slate-800/80 flex flex-col shrink-0">
        {/* Brand Header */}
        <div className="h-16 px-5 border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between">
          <Logo size="sm" />
          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">
            Console
          </span>
        </div>

        {/* Navigation List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
            Platform Views
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-slate-900 text-white dark:bg-brand-600 dark:text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.count !== undefined && item.count > 0 && (
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                    isActive ? 'bg-white/20 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                  }`}>
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-slate-200/80 dark:border-slate-800/80 space-y-2">
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200/80 dark:border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-semibold text-slate-700 dark:text-slate-300">Sandbox</span>
            </div>
            <span className="font-mono text-[10px] text-slate-400">Port 48080</span>
          </div>

          <button
            onClick={onBackToLanding}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-200 dark:hover:border-slate-700"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Landing Page</span>
          </button>
        </div>
      </aside>

      {/* Main App Container */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top App Header */}
        <header className="h-16 bg-white dark:bg-[#0D121F] border-b border-slate-200/80 dark:border-slate-800/80 px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-bold text-slate-900 dark:text-slate-100 capitalize">
              {currentTab === 'settings' ? 'LLM & API Key Configuration' : currentTab.replace('-', ' ')}
            </h1>
            <span className="text-slate-300 dark:text-slate-700">·</span>
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              {verifiedFindingsCount > 0 ? `Active Findings: ${verifiedFindingsCount}` : 'No Active Scan'}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle darkMode={darkMode} setDarkMode={setDarkMode} />
            <button
              onClick={() => setCurrentTab('new-scan')}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 transition-colors shadow-xs"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Launch Scan</span>
            </button>
          </div>
        </header>

        {/* Tab Content View */}
        <main className={`flex-1 p-6 md:p-8 flex flex-col justify-between ${
          currentTab === 'ai-chat' ? 'overflow-hidden' : 'overflow-y-auto'
        }`}>
          <div className={currentTab === 'ai-chat' ? 'flex-1 flex flex-col min-h-0' : ''}>
            {children}
          </div>

          {/* Social Links & Proprietor Footer in App Console */}
          {currentTab !== 'ai-chat' && (
            <div className="mt-16 pt-8 border-t border-slate-200/80 dark:border-slate-800/80 flex justify-center">
              <SocialFooterStrip />
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
