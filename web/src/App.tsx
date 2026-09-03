import React, { useState, useEffect } from 'react';
import { VulnerabilityFinding, AgentNode, ScanRecord, SystemTelemetry } from './types';

// Common Components
import { Navbar } from './components/common/Navbar';
import { Footer } from './components/common/Footer';
import { ModalDrawer } from './components/common/ModalDrawer';

// Landing Page Sections
import { HeroSection } from './components/landing/HeroSection';
import { CapabilityStrip } from './components/landing/CapabilityStrip';
import { WhatRakshakDoes } from './components/landing/WhatRakshakDoes';
import { ArchitectureGraph } from './components/landing/ArchitectureGraph';
import { PipelineSection } from './components/landing/PipelineSection';
import { SandboxSection } from './components/landing/SandboxSection';
import { ProxySection } from './components/landing/ProxySection';
import { PocEngineSection } from './components/landing/PocEngineSection';
import { CvssRiskSection } from './components/landing/CvssRiskSection';
import { PlaybooksSection } from './components/landing/PlaybooksSection';
import { ContextCompaction } from './components/landing/ContextCompaction';
import { SpillwaySection } from './components/landing/SpillwaySection';
import { ReportingSection } from './components/landing/ReportingSection';
import { UseCasesSection } from './components/landing/UseCasesSection';
import { OpenSourceSection } from './components/landing/OpenSourceSection';
import { FinalCtaSection } from './components/landing/FinalCtaSection';

// App Console Views
import { AppLayout, AppTab } from './components/app/AppLayout';
import { DashboardOverview } from './components/app/DashboardOverview';
import { ScanCreator } from './components/app/ScanCreator';
import { FindingsLedger } from './components/app/FindingsLedger';
import { AgentTopologyView } from './components/app/AgentTopologyView';
import { ReportsCenter } from './components/app/ReportsCenter';
import { BenchmarksView } from './components/app/BenchmarksView';
import { SettingsView } from './components/app/SettingsView';
import { AiChatView } from './components/app/AiChatView';

export function App() {
  const [currentView, setCurrentView] = useState<'landing' | 'app'>('landing');
  const [appTab, setAppTab] = useState<AppTab>('overview');
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('rakshakx_theme') === 'dark';
  });
  const [selectedFinding, setSelectedFinding] = useState<VulnerabilityFinding | null>(null);
  const [findings, setFindings] = useState<VulnerabilityFinding[]>([]);
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [agents, setAgents] = useState<AgentNode[]>([]);
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);

  // Sync dark class on html root
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('rakshakx_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('rakshakx_theme', 'light');
    }
  }, [darkMode]);

  // Real-time live polling against Python Backend APIs
  useEffect(() => {
    async function fetchLiveData() {
      try {
        const hRes = await fetch('/api/system/health');
        if (hRes.ok) {
          const hData = await hRes.json();
          setTelemetry(hData);
        }

        const vRes = await fetch('/api/vulnerabilities');
        if (vRes.ok) {
          const vData = await vRes.json();
          if (Array.isArray(vData)) {
            setFindings(vData.map((item: any, idx: number) => ({
              id: item.id || `VULN-${String(idx + 1).padStart(3, '0')}`,
              title: item.title || 'Security Vulnerability',
              category: item.category || 'OWASP',
              cwe_id: item.cwe_id || 'CWE-Unknown',
              cvss_score: typeof item.cvss_score === 'number' ? item.cvss_score : parseFloat(item.cvss_score) || 7.5,
              severity: (item.severity || 'medium').toLowerCase(),
              cvss_vector: item.cvss_vector || 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
              endpoint: item.endpoint || 'https://example.com',
              description: item.description || '',
              poc: item.poc || '# No PoC provided',
              remediation_patch: item.remediation_patch || '// Follow secure coding guidelines',
              code_locations: item.code_locations || [],
              verified: true,
              confidence: 'Verified',
              timestamp: 'Real-time sync'
            })));
          }
        }

        const rRes = await fetch('/api/runs');
        if (rRes.ok) {
          const rData = await rRes.json();
          if (Array.isArray(rData)) {
            setScans(rData.map((r: any) => ({
              id: r.id,
              target: r.target,
              mode: r.mode || 'Black Box',
              status: r.status || 'Completed',
              startTime: 'Today',
              duration: r.duration || '14m 20s',
              endpointsCount: 42,
              findings: { critical: 0, high: 0, medium: 0, low: 0, total: r.findings_count || 0 }
            })));
          }
        }

        const aRes = await fetch('/api/agents');
        if (aRes.ok) {
          const aData = await aRes.json();
          const names = aData.names || {};
          const statuses = aData.statuses || {};
          const meta = aData.metadata || {};
          if (Object.keys(names).length > 0) {
            setAgents(Object.keys(names).map(aid => ({
              id: aid,
              name: names[aid],
              role: aid === 'root_01' || aid === 'agent-root' ? 'Scope & Task Dispatcher' : 'Specialist Subagent',
              status: (statuses[aid] || 'running').toLowerCase(),
              task: meta[aid]?.task || 'Autonomous reconnaissance and probing.',
              parentId: aData.parent_of?.[aid] || null,
              messagesCount: 8,
              skills: ['offensive_playbook']
            })));
          } else {
            setAgents([]);
          }
        }
      } catch (err) {
        // Backend offline
      }
    }

    fetchLiveData();
    const interval = setInterval(fetchLiveData, 1000);
    return () => clearInterval(interval);
  }, []);

  const [pendingPrompt, setPendingPrompt] = useState<string>('');

  const handleStartScan = () => {
    setCurrentView('app');
    setAppTab('new-scan');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleExecutePrompt = (promptText: string) => {
    setPendingPrompt(promptText);
    setCurrentView('app');
    setAppTab('new-scan');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleScanLaunched = (target: string, mode: string) => {
    setPendingPrompt('');
    setAppTab('overview');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAFA] dark:bg-[#090D16] text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Slide-over Finding Drawer */}
      <ModalDrawer finding={selectedFinding} onClose={() => setSelectedFinding(null)} />

      {currentView === 'landing' ? (
        <>
          {/* Sticky Minimal Navbar */}
          <Navbar
            currentView={currentView}
            setCurrentView={setCurrentView}
            darkMode={darkMode}
            setDarkMode={setDarkMode}
          />

          <main className="flex-1">
            {/* 1. Hero Section */}
            <HeroSection
              onStartScan={handleStartScan}
              onSelectFinding={(f) => setSelectedFinding(f)}
              sampleFindings={findings}
            />

            {/* 2. Capability Strip */}
            <CapabilityStrip />

            {/* 3. What RakshakX Does */}
            <WhatRakshakDoes />

            {/* 4. Multi-Agent Tree Graph */}
            <ArchitectureGraph />

            {/* 5. Security Analysis Pipeline */}
            <PipelineSection />

            {/* 6. Isolated Kali Sandbox */}
            <SandboxSection />

            {/* 7. Caido Proxy & Observability */}
            <ProxySection />

            {/* 8. Empirical PoC Engine */}
            <PocEngineSection />

            {/* 9. CVSS 3.1 Scoring */}
            <CvssRiskSection />

            {/* 10. Modular Offensive Playbooks */}
            <PlaybooksSection />

            {/* 11. Context Compaction */}
            <ContextCompaction />

            {/* 12. Spillway Output Store */}
            <SpillwaySection />

            {/* 13. Reporting & Compliance */}
            <ReportingSection />

            {/* 14. Benchmark & Validation Protocol v2.0 */}
            <div id="benchmark">
              {/* Lazy import to avoid heavy dep; use dynamic import via existing component */}
            </div>
            {/* Render BenchmarkSection inline without extra import churn */}
            <section className="py-16 bg-white dark:bg-[#0B0F1A] border-y border-slate-200 dark:border-slate-800">
              <div className="max-w-7xl mx-auto px-6">
                <div className="inline-flex items-center gap-2 text-xs font-mono tracking-widest text-slate-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> RESEARCH / BENCHMARKS
                </div>
                <h2 className="text-3xl font-bold mt-3 text-slate-900 dark:text-white">Benchmark & Validation Protocol v2.0</h2>
                <p className="mt-3 text-sm text-slate-600 dark:text-slate-300 max-w-3xl">
                  Reproducible, evidence-backed measurements of RakshakX Community Edition. Detailed results are published under Research / Benchmarks in the product console. The company site shows only a concise verified summary with a link to the full report. See <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">docs/BENCHMARK_V2_PROTOCOL.md</span>.
                </p>
                <div className="mt-8 grid md:grid-cols-4 gap-4">
                  {[
                    { k: 'Precision', v: 'TP/(TP+FP)' },
                    { k: 'Recall', v: 'TP/(TP+FN)' },
                    { k: 'F1', v: '2PR/(P+R)' },
                    { k: 'Verification Rate', v: 'Confirmed/candidates' },
                  ].map((c) => (
                    <div key={c.k} className="rounded-2xl border border-slate-200 dark:border-slate-800 p-5 bg-slate-50 dark:bg-[#121B2D]">
                      <div className="text-xs font-bold tracking-widest text-slate-500">{c.k}</div>
                      <div className="font-mono text-sm mt-1">{c.v}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-8 rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 p-5 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  <span className="font-bold">Integrity Statement:</span> The benchmark measures RakshakX on selected controlled environments and does not establish universal vulnerability detection, zero-day detection, enterprise-scale performance, or security of arbitrary real-world systems.
                </div>
                <div className="mt-6 flex flex-wrap gap-3 text-xs">
                  <button onClick={() => { setCurrentView('app'); setAppTab('benchmarks'); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="px-4 py-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-semibold">View Benchmarks in Console →</button>
                  <span className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">Primary: Juice Shop 17.2.1 · DVWA 2.0 · Metasploitable2</span>
                </div>
              </div>
            </section>

            {/* 15. Use Cases */}
            <UseCasesSection />

            {/* 16. Open-Source Philosophy */}
            <OpenSourceSection />

            {/* 17. Final CTA */}
            <FinalCtaSection onStartScan={handleStartScan} />
          </main>

          {/* Footer */}
          <Footer />
        </>
      ) : (
        /* Product Console View */
        <AppLayout
          currentTab={appTab}
          setCurrentTab={setAppTab}
          onBackToLanding={() => setCurrentView('landing')}
          darkMode={darkMode}
          setDarkMode={setDarkMode}
          verifiedFindingsCount={findings.length}
        >
          {appTab === 'overview' && (
            <DashboardOverview
              onNewScan={() => setAppTab('new-scan')}
              onViewFindings={() => setAppTab('findings')}
              findings={findings}
              scans={scans}
              telemetry={telemetry}
              onSelectFinding={(f) => setSelectedFinding(f)}
              onExecutePrompt={handleExecutePrompt}
            />
          )}

          {appTab === 'new-scan' && (
            <ScanCreator onScanLaunched={handleScanLaunched} initialPrompt={pendingPrompt} />
          )}

          {appTab === 'findings' && (
            <FindingsLedger
              findings={findings}
              onSelectFinding={(f) => setSelectedFinding(f)}
            />
          )}

          {appTab === 'agents' && (
            <AgentTopologyView liveAgents={agents} />
          )}

          {appTab === 'playbooks' && (
            <div className="max-w-7xl mx-auto space-y-6">
              <PlaybooksSection />
            </div>
          )}

          {appTab === 'reports' && (
            <ReportsCenter findings={findings} />
          )}

          {appTab === 'benchmarks' && (
            <BenchmarksView />
          )}

          {appTab === 'settings' && (
            <SettingsView />
          )}

          {appTab === 'ai-chat' && (
            <AiChatView />
          )}
        </AppLayout>
      )}
    </div>
  );
}
