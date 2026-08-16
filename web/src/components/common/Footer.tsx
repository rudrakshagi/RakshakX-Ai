import React from 'react';
import { Github, Heart, Terminal, BookOpen, Scale, FileText } from 'lucide-react';
import { Logo } from './Logo';
import { SocialFooterStrip } from './SocialFooterStrip';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-white dark:bg-[#070A10] border-t border-slate-200/80 dark:border-slate-800/80 transition-colors py-14">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand Col */}
          <div className="col-span-2 space-y-3">
            <Logo size="md" />
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed">
              Community & Open-Source Edition of <strong>Trinetra AI</strong>. Designed and architected by Parent Company <a href="https://rudrakshai.in" target="_blank" rel="noreferrer" className="text-brand-600 dark:text-brand-400 font-bold hover:underline">Rudraksh AGI (rudrakshai.in)</a> · Proprietor: <strong>Aditya Kumar Mishra</strong>.
            </p>
            <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-500 dark:text-slate-400 font-mono">
              <span className="inline-flex items-center gap-1">
                <Scale className="w-3.5 h-3.5 text-brand-500" /> Rudraksh AGI Community License
              </span>
              <span>·</span>
              <span>Non-Commercial</span>
            </div>
          </div>

          {/* Col 1: Product */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-200">
              Product
            </h4>
            <ul className="space-y-2 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              <li><a href="#features" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Features</a></li>
              <li><a href="#architecture" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Multi-Agent Graph</a></li>
              <li><a href="#pipeline" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Security Pipeline</a></li>
              <li><a href="#sandbox" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Kali Sandbox</a></li>
              <li><a href="#reporting" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">SARIF & PDF Reports</a></li>
            </ul>
          </div>

          {/* Col 2: Playbooks */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-200">
              Playbooks
            </h4>
            <ul className="space-y-2 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              <li><a href="#playbooks" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Authentication & JWT</a></li>
              <li><a href="#playbooks" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">SQL Injection</a></li>
              <li><a href="#playbooks" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">SSRF & Metadata</a></li>
              <li><a href="#playbooks" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Race Conditions</a></li>
              <li><a href="#playbooks" className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">IDOR / BOLA</a></li>
            </ul>
          </div>

          {/* Col 3: Community & Docs */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-200">
              Community
            </h4>
            <ul className="space-y-2 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              <li>
                <a
                  href="https://github.com/rakshakx/rakshakx"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
                >
                  <Github className="w-3.5 h-3.5" /> GitHub Repository
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/rakshakx/rakshakx/blob/main/CONTRIBUTING.md"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
                >
                  Contributing Guide
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/rakshakx/rakshakx/discussions"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
                >
                  Discussions & Support
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/rakshakx/rakshakx/blob/main/SECURITY.md"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
                >
                  Security Policy
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Social Links & Proprietor Attribution */}
        <div className="py-8 border-t border-slate-200/80 dark:border-slate-800/80 flex justify-center">
          <SocialFooterStrip />
        </div>

        {/* Bottom Bar */}
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <div>
            © {new Date().getFullYear()} RakshakX (Rakshak AI) · Community Edition of Trinetra AI.
          </div>
          <div className="flex items-center gap-4">
            <span>Only test systems you have explicit authorization to assess.</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
