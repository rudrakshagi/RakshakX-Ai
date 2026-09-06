import React, { useState, useEffect, useRef } from 'react';
import { Terminal, RefreshCw, Download, Filter, Search, CheckCircle2, AlertCircle, Info, Shield, Trash2, Pause, Play } from 'lucide-react';

export interface LogItem {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
  source: string;
  message: string;
  raw?: string;
}

export const LiveLogsConsole: React.FC = () => {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [backendHealth, setBackendHealth] = useState<any>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Poll backend health & logs
  useEffect(() => {
    let cancelled = false;

    async function fetchHealth() {
      try {
        const res = await fetch('/api/system/health');
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setBackendHealth(data);
        }
      } catch {}
    }

    async function fetchLogs() {
      if (isPaused) return;
      setIsLoading(true);
      try {
        let logList: LogItem[] = [];
        const res = await fetch(`/v1/logs?source=${sourceFilter}&lines=200`);
        if (res.ok) {
          const data = await res.json();
          if (data && Array.isArray(data.logs)) {
            logList = data.logs;
          }
        } else {
          const apiRes = await fetch(`/api/logs?source=${sourceFilter}&lines=200`);
          if (apiRes.ok) {
            const aData = await apiRes.json();
            if (aData && Array.isArray(aData.logs)) {
              logList = aData.logs;
            }
          }
        }
        if (!cancelled) setLogs(logList);
      } catch (e) {
        try {
          const apiRes = await fetch(`/api/logs?source=${sourceFilter}&lines=200`);
          if (apiRes.ok) {
            const aData = await apiRes.json();
            if (aData && Array.isArray(aData.logs) && !cancelled) {
              setLogs(aData.logs);
            }
          }
        } catch {}
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchHealth();
    fetchLogs();

    const interval = setInterval(() => {
      fetchHealth();
      fetchLogs();
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [sourceFilter, isPaused]);

  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolledUpRef = useRef<boolean>(false);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    userScrolledUpRef.current = !isAtBottom;
    if (isAtBottom && !autoScroll) {
      setAutoScroll(true);
    } else if (!isAtBottom && autoScroll) {
      setAutoScroll(false);
    }
  };

  useEffect(() => {
    if (autoScroll && !isPaused && !userScrolledUpRef.current) {
      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight;
      }
    }
  }, [logs, autoScroll, isPaused]);

  const filteredLogs = logs.filter((item) => {
    const matchesSearch =
      !searchQuery ||
      item.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.source.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const handleDownload = () => {
    const text = logs.map((l) => `[${l.timestamp}] [${l.level}] [${l.source}] ${l.message}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rakshakx_system_logs_${Date.now()}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClear = () => {
    setLogs([]);
  };

  return (
    <div className="flex flex-col h-full space-y-4 animate-fadeIn">
      {/* Top Status & System Health Strip */}
      <div className="p-4 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-900 dark:bg-brand-600/20 text-brand-500 border border-brand-500/30 flex items-center justify-center shrink-0">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <span>Real-time System & Agent Execution Logs</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                LIVE STREAM
              </span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Live stdout/stderr tailing from <code className="font-mono text-brand-400">logs/backend.log</code>, <code className="font-mono text-brand-400">logs/bridge.log</code>, and Docker Sandbox.
            </p>
          </div>
        </div>

        {backendHealth && (
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-slate-400">Backend:</span>
              <span className="font-bold text-slate-200">PID {backendHealth.backend?.pid ?? '26741'}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <Shield className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-slate-400">Container:</span>
              <span className="font-bold text-cyan-300 truncate max-w-[140px]">
                {backendHealth.sandbox?.container ?? 'rakshakx/sandbox'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Control & Filter Header */}
      <div className="p-3.5 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex flex-wrap items-center gap-2">
          {/* Source Tabs */}
          {[
            { id: 'all', label: 'All Sources' },
            { id: 'backend', label: 'Python Backend' },
            { id: 'bridge', label: 'OpenCode Bridge' },
            { id: 'scan', label: 'Docker Sandbox' },
            { id: 'frontend', label: 'Frontend UI' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSourceFilter(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                sourceFilter === tab.id
                  ? 'bg-slate-900 text-white dark:bg-brand-600 dark:text-white shadow-xs'
                  : 'bg-slate-50 dark:bg-[#121B2D] text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search log stream..."
              className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500 w-36 sm:w-48"
            />
          </div>

          {/* Pause/Resume Toggle */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-2 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              isPaused
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-slate-50 dark:bg-[#121B2D] text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700'
            }`}
            title={isPaused ? 'Resume live log stream' : 'Pause log stream'}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{isPaused ? 'Resume' : 'Pause'}</span>
          </button>

          {/* Download Logs */}
          <button
            onClick={handleDownload}
            title="Download Log File"
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-[#121B2D] dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          {/* Clear Logs */}
          <button
            onClick={handleClear}
            title="Clear view"
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-[#121B2D] dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Terminal Window */}
      <div className="flex-1 min-h-[420px] rounded-2xl bg-slate-950 border border-slate-800 shadow-inner p-4 flex flex-col justify-between overflow-hidden font-mono">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3 text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="ml-2 font-bold text-slate-300">bash - /home/suryansh/RakshakX-Ai/logs</span>
          </div>
          <div className="flex items-center gap-3 text-[10px]">
            <span>Total Lines: {filteredLogs.length}</span>
            <label className="flex items-center gap-1 select-none cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-brand-500"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>

        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto space-y-1.5 pr-2 scrollbar-thin scrollbar-thumb-slate-800 font-mono text-[11px] leading-relaxed"
        >
          {filteredLogs.length === 0 ? (
            <div className="py-16 text-center text-slate-500 space-y-2">
              <Terminal className="w-8 h-8 mx-auto text-slate-700 animate-pulse" />
              <p>Listening for live execution log events from backend & sandbox...</p>
            </div>
          ) : (
            filteredLogs.map((item, idx) => {
              const levelColor =
                item.level === 'ERROR'
                  ? 'text-red-400 bg-red-500/10 border-red-500/30'
                  : item.level === 'WARN'
                  ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                  : item.level === 'SUCCESS'
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                  : 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';

              return (
                <div key={idx} className="flex items-start gap-2 hover:bg-slate-900/60 p-1 rounded transition-colors group">
                  <span className="text-slate-500 shrink-0 select-none text-[10px]">{item.timestamp}</span>
                  <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border shrink-0 ${levelColor}`}>
                    {item.level}
                  </span>
                  <span className="text-slate-400 font-bold shrink-0 text-[10px]">[{item.source}]</span>
                  <span className="text-slate-200 break-all select-text font-mono flex-1">{item.message}</span>
                </div>
              );
            })
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
};
export default LiveLogsConsole;

