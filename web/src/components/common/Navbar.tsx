import React from 'react';
import { Github, LayoutDashboard, ArrowRight } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { Logo } from './Logo';

interface NavbarProps {
  currentView: 'landing' | 'app';
  setCurrentView: (view: 'landing' | 'app') => void;
  darkMode: boolean;
  setDarkMode: (val: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  setCurrentView,
  darkMode,
  setDarkMode,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full bg-white/80 dark:bg-[#090D16]/80 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div
          onClick={() => setCurrentView('landing')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <Logo size="md" />
          <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-full border border-slate-200 dark:border-slate-700">
            Open Source
          </span>
        </div>

        {/* Center Nav Links (when on landing) */}
        {currentView === 'landing' ? (
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-slate-600 dark:text-slate-400">
            <a
              href="#features"
              className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
            >
              Features
            </a>
            <a
              href="#architecture"
              className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
            >
              Architecture
            </a>
            <a
              href="#pipeline"
              className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
            >
              Pipeline
            </a>
            <a
              href="#playbooks"
              className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
            >
              Playbooks
            </a>
            <a
              href="#use-cases"
              className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
            >
              Use Cases
            </a>
          </nav>
        ) : (
          <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Live Assessment Environment</span>
          </div>
        )}

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          <ThemeToggle darkMode={darkMode} setDarkMode={setDarkMode} />

          <a
            href="https://github.com/rakshakx/rakshakx"
            target="_blank"
            rel="noreferrer"
            className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors border border-slate-200/80 dark:border-slate-800 hidden sm:flex items-center gap-1.5 text-xs font-medium"
            title="GitHub Repository"
          >
            <Github className="w-4 h-4" />
            <span className="hidden lg:inline">Star</span>
          </a>

          {currentView === 'landing' ? (
            <button
              onClick={() => setCurrentView('app')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 shadow-sm transition-all hover:shadow-md"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Launch Dashboard</span>
            </button>
          ) : (
            <button
              onClick={() => setCurrentView('landing')}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 transition-colors border border-slate-200 dark:border-slate-700"
            >
              <span>Back to Home</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
