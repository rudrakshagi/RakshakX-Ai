import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, Sparkles, Terminal, Trash2, Cpu, RefreshCw, AlertTriangle, Search, Brain, ChevronDown, History, Plus, MessageSquare, Download, Copy, Check, RotateCcw, PanelLeftClose, PanelLeft, Wrench } from 'lucide-react';
import { splitThinking } from './thinkingParser';
import { CHAT_APPROVAL_STORAGE_KEY, buildApprovalBody, parseToolCallsFromMessage } from '../../data/chatTools';
import type { ChatToolCall } from '../../data/chatTools';
import { LiveLogsConsole } from './LiveLogsConsole';

interface Model {
  id: string;
  owned_by: string;
}

interface OpenAIToolCall {
  id: string;
  type: string;
  function: { name: string; arguments: string };
}

interface Message {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  /** Chain-of-thought streamed separately (delta.reasoning). Rendered in a think block. */
  thinking?: string;
  model?: string;
  timestamp: string;
  /** OpenAI-style tool calls emitted by the assistant (bridge auto-inject). */
  tool_calls?: OpenAIToolCall[];
  /** Legacy alias kept for backwards-compat with stored sessions. */
  toolCalls?: { id: string; name: string; args: string }[];
  /** For role === 'tool': which call this result belongs to. */
  tool_call_id?: string;
  toolName?: string;
}

interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  model: string;
  messages: Message[];
}

interface AgentInfo {
  id: string;
  name: string;
  type: string;
  status: string;
  action: string;
  currentTool?: string;
  progress?: number;
  logs?: string[];
}

const STORAGE_KEY = 'rakshakx_chat_sessions_v1';

/** Collapsible block that holds the model's leaked chain-of-thought
 *  separately from the final answer. Open while streaming, collapsed after. */
const ThinkingBlock: React.FC<{ thinking: string; defaultOpen: boolean }> = ({ thinking, defaultOpen }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-2 rounded-xl border border-violet-200/70 dark:border-violet-900/50 bg-violet-50/60 dark:bg-violet-950/20 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-600 dark:text-violet-400 hover:bg-violet-100/60 dark:hover:bg-violet-900/20 transition-colors"
      >
        <Brain className="w-3.5 h-3.5" />
        <span>Thinking</span>
        <ChevronDown className={`w-3.5 h-3.5 ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-2.5 pt-0.5 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400 whitespace-pre-wrap select-text font-mono">
          {thinking}
        </div>
      )}
    </div>
  );
};

/** Collapsible block listing assistant tool calls (reuse ThinkingBlock pattern). */
const ToolActivityBlock: React.FC<{
  calls: { id: string; name: string; args: string }[];
  resultSnippets?: Record<string, string>;
  defaultOpen: boolean;
}> = ({ calls, resultSnippets, defaultOpen }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-2 rounded-xl border border-sky-200/70 dark:border-sky-900/50 bg-sky-50/60 dark:bg-sky-950/20 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400 hover:bg-sky-100/60 dark:hover:bg-sky-900/20 transition-colors"
      >
        <Wrench className="w-3.5 h-3.5" />
        <span>Tool activity · {calls.length}</span>
        <ChevronDown className={`w-3.5 h-3.5 ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-2.5 pt-0.5 space-y-2">
          {calls.map((c) => (
            <div key={c.id} className="text-[11px] leading-relaxed">
              <div className="font-mono font-bold text-slate-700 dark:text-slate-300 truncate">
                {c.name}
              </div>
              {c.args && (
                <pre className="mt-1 p-2 rounded-lg bg-slate-950 text-slate-200 font-mono text-[10px] overflow-x-auto whitespace-pre-wrap break-all max-h-32 overflow-y-auto">
                  {c.args}
                </pre>
              )}
              {resultSnippets?.[c.id] ? (
                <div className="mt-1.5 p-2 rounded bg-slate-950 text-emerald-400 font-mono text-[10px] whitespace-pre-wrap break-all max-h-36 overflow-y-auto border border-slate-800">
                  <div className="text-[9px] uppercase font-bold text-slate-500 mb-0.5">Output Result</div>
                  → {resultSnippets[c.id]}
                </div>
              ) : (
                <div className="mt-1 text-slate-400 font-mono text-[10px] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                  <span>Executing command & waiting for tool result...</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/** Small muted block for role === 'tool' result messages. */
const ToolResultBlock: React.FC<{ toolName?: string; content: string }> = ({ toolName, content }) => {
  const [expanded, setExpanded] = useState(false);
  const truncated = content.length > 800 && !expanded;
  return (
    <div className="rounded-xl border border-slate-200/70 dark:border-slate-800 bg-slate-100/70 dark:bg-slate-800/40 px-3 py-2">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
        <Terminal className="w-3 h-3" />
        <span>{toolName ? `tool · ${toolName}` : 'tool result'}</span>
        {content.length > 800 && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="ml-auto normal-case tracking-normal font-semibold text-brand-600 dark:text-brand-400 hover:underline"
          >
            {expanded ? 'Show less' : 'Expand'}
          </button>
        )}
      </div>
      <div className="mt-1 font-mono text-[11px] leading-relaxed text-slate-600 dark:text-slate-300 whitespace-pre-wrap break-all select-text">
        {truncated ? content.slice(0, 800) + '…' : content}
      </div>
    </div>
  );
};

/** Inline subagent monitor block rendered directly inside the chat message feed when active subagents run */
const InlineSubagentMonitor: React.FC<{ agents: AgentInfo[]; defaultOpen?: boolean }> = ({ agents, defaultOpen = true }) => {
  const [open, setOpen] = useState(defaultOpen);
  const activeAgents = agents || [];
  if (activeAgents.length === 0) return null;
  return (
    <div className="mb-3 rounded-xl border border-emerald-500/40 bg-emerald-950/20 text-slate-200 overflow-hidden shadow-xs animate-fadeIn">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-emerald-400 hover:bg-emerald-900/30 transition-colors"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span>Active Agent Processes ({activeAgents.length})</span>
        <ChevronDown className={`w-3.5 h-3.5 ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="p-3 pt-1 grid grid-cols-1 gap-2.5">
          {activeAgents.map((ag) => {
            const statusBg =
              ag.status === 'executing_tool'
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : ag.status === 'running'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : ag.status === 'thinking'
                ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
            return (
              <div
                key={ag.id}
                className="p-3 rounded-xl bg-slate-900/95 border border-slate-800 space-y-2 text-xs shadow-md"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 truncate">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    <span className="font-bold text-slate-100 text-xs truncate">{ag.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">({ag.type})</span>
                  </div>
                  <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full border ${statusBg}`}>
                    {ag.status.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed font-mono">
                  <strong className="text-slate-400">Task:</strong> {ag.action}
                </p>
                {ag.progress !== undefined && (
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-emerald-400 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, Math.max(5, ag.progress))}%` }}
                    />
                  </div>
                )}
                {ag.currentTool && (
                  <div className="text-[11px] font-mono text-brand-300 bg-brand-500/10 px-2 py-1 rounded-lg border border-brand-500/30 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-brand-400 animate-spin" />
                    <span>Executing Tool: <strong>{ag.currentTool}</strong></span>
                  </div>
                )}
                {ag.logs && ag.logs.length > 0 && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-950 font-mono text-[11px] space-y-1 max-h-36 overflow-y-auto border border-slate-800 scrollbar-thin">
                    <div className="text-[9px] uppercase font-bold text-slate-400 tracking-wider flex items-center justify-between mb-1 pb-1 border-b border-slate-800">
                      <div className="flex items-center gap-1.5 text-emerald-400">
                        <Terminal className="w-3 h-3" />
                        <span>Live Execution Trace ({ag.logs.length} events)</span>
                      </div>
                      <span className="text-slate-500">Step-by-step</span>
                    </div>
                    {ag.logs.slice(-6).map((log, lIdx) => (
                      <div key={lIdx} className="text-emerald-400/90 leading-relaxed break-all font-mono flex items-start gap-1.5">
                        <span className="text-slate-600 text-[10px] select-none">#{lIdx + 1}</span>
                        <span>{log}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
/** Code block with one-click copy button */
const CodeBlock: React.FC<{ code: string }> = ({ code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-xl bg-slate-950 text-slate-100 border border-slate-800 font-mono text-xs overflow-hidden">
      <div className="flex items-center justify-between px-4 py-1.5 bg-slate-900/80 border-b border-slate-800/80 text-[10px] text-slate-400 select-none">
        <span>code</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <pre className="p-4 overflow-x-auto select-text">
        <code>{code}</code>
      </pre>
    </div>
  );
};

/** Burst-pacing tuning for the chat typewriter (see handleStreamResponse).
 *  Upstream (OpenCode Zen) buffers the full answer and flushes it in one
 *  burst, so arrivals larger than the threshold are revealed word-by-word
 *  instead of popping in all at once. Small incremental deltas pass through. */
const PACING_THRESHOLD_CHARS = 120;
const PACING_SLICE_CHARS = 12;
const PACING_FRAME_MS = 15;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Advance `from` by ~slice chars, stopping at a word boundary for smooth reveal. */
const nextRevealBoundary = (text: string, from: number, slice: number) => {
  let n = Math.min(text.length, from + slice);
  while (n < text.length && text[n] !== ' ' && text[n] !== '\n' && n - from < slice * 4) n++;
  return n;
};

export const AiChatView: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelSearch, setModelSearch] = useState('');
  const [showFreeOnly, setShowFreeOnly] = useState(true);
  const [showSidebar, setShowSidebar] = useState(false);
  const [liveAgents, setLiveAgents] = useState<AgentInfo[]>([]);
  const [showAgentsPanel, setShowAgentsPanel] = useState<boolean>(true);
  const [showLogsConsole, setShowLogsConsole] = useState<boolean>(false);

  // Chat sessions state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');

  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I am RakshakX Security Assistant. Select an AI model and ask me anything about code security, vulnerability patching, or penetration testing.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [inputValue, setInputValue] = useState('');
  const [stream, setStream] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingSecs, setThinkingSecs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isFetchingModels, setIsFetchingModels] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const API_BASE_URL = '';

  // Poll live agent graph status (/v1/agents or /api/agents)
  useEffect(() => {
    let cancelled = false;
    async function fetchAgents() {
      try {
        const res = await fetch('/v1/agents');
        if (res.ok) {
          const data = await res.json();
          if (data && !cancelled) {
            if (Array.isArray(data.data)) {
              setLiveAgents(data.data);
              return;
            }
            if (data.data && typeof data.data === 'object' && data.data.names) {
              const names = data.data.names || {};
              const statuses = data.data.statuses || {};
              const meta = data.data.metadata || {};
              const agentKeys = Object.keys(names);
              setLiveAgents(
                agentKeys.map((aid) => ({
                  id: aid,
                  name: names[aid] || aid,
                  type: aid === 'root_01' || aid === 'agent-root' || aid.includes('root') ? 'Root Orchestrator' : 'Specialist Subagent',
                  status: (statuses[aid] || 'completed').toLowerCase(),
                  action: meta[aid]?.task || meta[aid]?.action || 'Executing security task...',
                  currentTool: meta[aid]?.current_tool,
                  progress: meta[aid]?.progress ?? (statuses[aid] === 'completed' ? 100 : 75),
                  logs: meta[aid]?.logs || [],
                }))
              );
              return;
            }
          }
        }

        const apiRes = await fetch('/api/agents');
        if (apiRes.ok) {
          const aData = await apiRes.json();
          const names = aData.names || {};
          const statuses = aData.statuses || {};
          const meta = aData.metadata || {};
          const agentKeys = Object.keys(names);
          if (!cancelled) {
            setLiveAgents(
              agentKeys.map((aid) => ({
                id: aid,
                name: names[aid] || aid,
                type: aid === 'root_01' || aid === 'agent-root' || aid.includes('root') ? 'Root Orchestrator' : 'Specialist Subagent',
                status: (statuses[aid] || 'completed').toLowerCase(),
                action: meta[aid]?.task || meta[aid]?.action || 'Executing security task...',
                currentTool: meta[aid]?.current_tool,
                progress: meta[aid]?.progress ?? (statuses[aid] === 'completed' ? 100 : 75),
                logs: meta[aid]?.logs || [],
              }))
            );
            return;
          }
        }

        if (!cancelled) setLiveAgents([]);
      } catch (e) {
        if (!cancelled) setLiveAgents([]);
      }
    }

    fetchAgents();
    const interval = setInterval(fetchAgents, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Agentic tool approval state (persisted; shared key with SettingsView)
  const [autoApprove, setAutoApprove] = useState<boolean>(
    () => localStorage.getItem(CHAT_APPROVAL_STORAGE_KEY) !== 'manual',
  );
  // Agentic tool-calling mode: when ON the bridge injects the RakshakX tool
  // schemas and runs the 6-turn agentic loop (otherwise plain chat, no tools).
  const [agenticMode, setAgenticMode] = useState<boolean>(
    () => localStorage.getItem('rakshakx_chat_agentic_mode') !== 'off',
  );
  const toggleAgenticMode = () => {
    setAgenticMode((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('rakshakx_chat_agentic_mode', next ? 'on' : 'off');
      } catch {}
      return next;
    });
  };
  const [pendingApprovals, setPendingApprovals] = useState<ChatToolCall[]>([]);
  const [decisions, setDecisions] = useState<Record<string, 'approve' | 'deny'>>({});

  const toggleAutoApprove = () => {
    setAutoApprove((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(CHAT_APPROVAL_STORAGE_KEY, next ? 'auto' : 'manual');
      } catch {}
      return next;
    });
  };

  // Load chat sessions from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: ChatSession[] = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSessions(parsed);
          setCurrentSessionId(parsed[0].id);
          setMessages(parsed[0].messages);
          if (parsed[0].model) setSelectedModel(parsed[0].model);
          return;
        }
      }
    } catch (e) {
      console.warn('Could not load chat sessions from localStorage:', e);
    }

    // Default initial session
    const initId = 'session_' + Date.now();
    const initSession: ChatSession = {
      id: initId,
      title: 'Security Consultation',
      createdAt: new Date().toLocaleDateString(),
      updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model: selectedModel,
      messages: [
        {
          role: 'assistant',
          content: 'Hello! I am RakshakX Security Assistant. Select an AI model and ask me anything about code security, vulnerability patching, or penetration testing.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ],
    };
    setSessions([initSession]);
    setCurrentSessionId(initId);
  }, []);

  // Save active session messages to localStorage whenever messages change
  useEffect(() => {
    if (!currentSessionId || messages.length === 0) return;

    setSessions((prevSessions) => {
      const updated = prevSessions.map((sess) => {
        if (sess.id === currentSessionId) {
          const firstUserMsg = messages.find((m) => m.role === 'user')?.content;
          const autoTitle = firstUserMsg
            ? firstUserMsg.slice(0, 28) + (firstUserMsg.length > 28 ? '...' : '')
            : sess.title;
          return {
            ...sess,
            title: autoTitle,
            model: selectedModel || sess.model,
            messages,
            updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
        }
        return sess;
      });

      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch (e) {
        console.warn('Error saving chat sessions to localStorage:', e);
      }
      return updated;
    });
  }, [messages, selectedModel, currentSessionId]);

  // Compute filtered models
  const filteredModels = models.filter((m) => {
    const matchesSearch = m.id.toLowerCase().includes(modelSearch.toLowerCase());
    const isFree = m.id.includes('-free') || m.id.includes('contributor-free') || m.id === 'oc/big-pickle';
    const matchesFree = !showFreeOnly || isFree;
    return matchesSearch && matchesFree;
  });

  // Fetch models on mount
  useEffect(() => {
    fetchModels();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Elapsed-time indicator while waiting for the first streamed token.
  // Upstream buffers the full answer (10s+ of silence is normal), so show
  // a live "Thinking… Ns" instead of a bare blinking cursor.
  useEffect(() => {
    if (!isLoading) return;
    const t0 = Date.now();
    setThinkingSecs(0);
    const id = setInterval(() => setThinkingSecs(Math.floor((Date.now() - t0) / 1000)), 500);
    return () => clearInterval(id);
  }, [isLoading]);

  // Auto-select first filtered model if current selection invalid
  useEffect(() => {
    if (filteredModels.length > 0 && !filteredModels.some((m) => m.id === selectedModel)) {
      setSelectedModel(filteredModels[0].id);
    }
  }, [modelSearch, showFreeOnly, models]);

  const fetchModels = async () => {
    setIsFetchingModels(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/v1/models`);
      if (!res.ok) {
        throw new Error(`Failed to fetch models (${res.status})`);
      }
      const data = await res.json();
      if (data && Array.isArray(data.data)) {
        setModels(data.data);
        const PREFERRED_MODELS = [
          'oc/nemotron-3.5-lightning-free',
          'oc/muse-spark-1.3-contributor-free',
          'oc/laguna-s-2.1-free',
          'oc/muse-spark-1.2-contributor-free',
        ];
        const ids = new Set(data.data.map((m: Model) => m.id));
        const defaultModel =
          PREFERRED_MODELS.find((id) => ids.has(id)) ??
          data.data.find((m: Model) => m.id.includes('-free') || m.id.includes('contributor-free'))?.id ??
          data.data[0]?.id ??
          '';
        setSelectedModel(defaultModel);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err: any) {
      console.error('Error fetching models:', err);
      setError('Could not connect to the bridge server. Ensure the bridge is running (proxied via /v1).');
    } finally {
      setIsFetchingModels(false);
    }
  };

  const createNewChat = () => {
    if (isLoading) handleCancelRequest();

    const newId = 'session_' + Date.now();
    const newSession: ChatSession = {
      id: newId,
      title: 'New Security Audit',
      createdAt: new Date().toLocaleDateString(),
      updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model: selectedModel,
      messages: [
        {
          role: 'assistant',
          content: 'Hello! I am RakshakX Security Assistant. Select an AI model and ask me anything about code security, vulnerability patching, or penetration testing.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ],
    };

    const updated = [newSession, ...sessions];
    setSessions(updated);
    setCurrentSessionId(newId);
    setMessages(newSession.messages);
    setError(null);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch (e) {}
  };

  const switchSession = (sess: ChatSession) => {
    if (isLoading) handleCancelRequest();
    setCurrentSessionId(sess.id);
    setMessages(sess.messages);
    if (sess.model) setSelectedModel(sess.model);
    setError(null);
  };

  const deleteSession = (sessId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const filtered = sessions.filter((s) => s.id !== sessId);
    if (filtered.length === 0) {
      createNewChat();
      return;
    }
    setSessions(filtered);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
    } catch (err) {}
    if (currentSessionId === sessId) {
      switchSession(filtered[0]);
    }
  };

  const exportCurrentChatMarkdown = () => {
    const lines = [`# RakshakX AI Security Chat Export\nDate: ${new Date().toLocaleString()}\nModel: ${selectedModel}\n\n---`];
    messages.forEach((m) => {
      lines.push(`\n### ${m.role === 'user' ? '👤 User' : '🤖 Assistant'} (${m.timestamp})\n`);
      if (m.thinking) {
        lines.push(`> **Thinking:**\n> ${m.thinking.replace(/\n/g, '\n> ')}\n`);
      }
      lines.push(m.content);
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rakshakx-chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /** Map UI messages to the API body, preserving tool_calls + role:'tool' entries. */
  const toApiMessages = (history: Message[]) =>
    history.map((m) => {
      const base: Record<string, unknown> = { role: m.role, content: m.content };
      if (m.tool_calls && m.tool_calls.length > 0) base.tool_calls = m.tool_calls;
      if (m.role === 'tool' && m.tool_call_id) base.tool_call_id = m.tool_call_id;
      return base;
    });

  const nowStamp = () =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  /** Non-streaming response handling: approvals, tool activity, final answer. */
  const handleNonStreamingData = (data: any) => {
    const choice = data?.choices?.[0];
    const finishReason: string | undefined = choice?.finish_reason;
    const msg = choice?.message ?? {};
    const assistantText: string = msg?.content ?? '';
    const assistantThinking: string =
      (typeof msg?.reasoning === 'string' && msg.reasoning) ||
      (Array.isArray(msg?.reasoning_details)
        ? msg.reasoning_details.map((p: any) => p?.text || '').join('')
        : '');
    const rawToolCalls: OpenAIToolCall[] | undefined = Array.isArray(msg?.tool_calls)
      ? msg.tool_calls
      : undefined;

    // Bridge asks for manual approval before executing tools.
    if (finishReason === 'approval_required') {
      const pending: ChatToolCall[] = Array.isArray(choice?.pending_approvals)
        ? choice.pending_approvals.map((p: any) => ({
            call_id: String(p?.call_id ?? p?.id ?? ''),
            name: String(p?.name ?? p?.function?.name ?? 'unknown_tool'),
            arguments: String(p?.arguments ?? p?.function?.arguments ?? ''),
          }))
        : parseToolCallsFromMessage({ tool_calls: rawToolCalls as any });
      if (rawToolCalls && rawToolCalls.length > 0) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: assistantText,
            thinking: assistantThinking || undefined,
            model: selectedModel,
            timestamp: nowStamp(),
            tool_calls: rawToolCalls,
          },
        ]);
      }
      setPendingApprovals(pending);
      return;
    }

    // Bridge may return intermediate executed tool results alongside the final answer.
    const executedTools: any[] = Array.isArray((data as any)?.executed_tools)
      ? (data as any).executed_tools
      : Array.isArray(msg?.executed_tools)
        ? msg.executed_tools
        : [];

    const toolMessages: Message[] = executedTools.map((t: any) => ({
      role: 'tool' as const,
      content: String(t?.result ?? t?.content ?? t?.output ?? ''),
      timestamp: nowStamp(),
      tool_call_id: String(t?.call_id ?? t?.tool_call_id ?? t?.id ?? ''),
      toolName: String(t?.name ?? t?.tool ?? 'tool'),
    }));

    // Auto mode: bridge executed tools server-side; surface activity via tool_calls + results.
    if (finishReason === 'tool_calls' || rawToolCalls?.length || toolMessages.length > 0) {
      const out: Message[] = [];
      if (rawToolCalls && rawToolCalls.length > 0) {
        out.push({
          role: 'assistant',
          content: assistantText,
          thinking: assistantThinking || undefined,
          model: selectedModel,
          timestamp: nowStamp(),
          tool_calls: rawToolCalls,
        });
      }
      out.push(...toolMessages);
      // If the bridge returned only intermediate messages, still append the final text.
      if (assistantText || out.length === 0) {
        out.push({
          role: 'assistant',
          content: assistantText,
          thinking: assistantThinking || undefined,
          model: selectedModel,
          timestamp: nowStamp(),
        });
      }
      setMessages((prev) => [...prev, ...out]);
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        role: 'assistant',
        content: assistantText,
        thinking: assistantThinking || undefined,
        model: selectedModel,
        timestamp: nowStamp(),
      },
    ]);
  };

  const postChat = async (
    history: Message[],
    approvalPayload: { mode: 'auto' | 'manual'; decisions: Record<string, 'approve' | 'deny'> },
    useStream: boolean,
    signal: AbortSignal,
  ): Promise<Response> => {
    // Agentic mode: ask the bridge to inject RakshakX tool schemas and run
    // its tool loop (use_rakshak_tools). OFF = plain chat, no tool calls.
    const requestBody = {
      model: selectedModel,
      messages: toApiMessages(history),
      stream: useStream,
      use_rakshak_tools: agenticMode,
      approval: approvalPayload,
    };
    return fetch(`${API_BASE_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal,
    });
  };

  const handleSendMessage = async (e?: React.FormEvent, customPrompt?: string, isResume?: boolean) => {
    if (e) e.preventDefault();
    if (isLoading) return;

    let history: Message[];
    if (isResume) {
      // Resume after approval: reuse full conversation (incl. tool_calls + tool results).
      history = [...messages];
    } else {
      const promptToSend = customPrompt || inputValue;
      if (!promptToSend.trim()) return;
      if (!selectedModel) {
        setError('Please select a model from the list.');
        return;
      }
      setError(null);
      if (!customPrompt) setInputValue('');
      history = [
        ...messages,
        { role: 'user', content: promptToSend.trim(), timestamp: nowStamp() },
      ];
      setMessages(history);
    }

    if (!selectedModel) {
      setError('Please select a model from the list.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      abortControllerRef.current = new AbortController();
      const approvalPayload = buildApprovalBody(autoApprove, decisions);
      const response = await postChat(history, approvalPayload, stream, abortControllerRef.current.signal);

      if (!response.ok) {
        let errMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errObj = await response.json();
          if (errObj.error?.message) errMessage = errObj.error.message;
        } catch {}
        throw new Error(errMessage);
      }

      if (stream) {
        await handleStreamResponse(response, abortControllerRef.current?.signal);
      } else {
        const data = await response.json();
        handleNonStreamingData(data);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Chat error:', err);
        setError(err.message || 'An error occurred while generating response.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  /** Resume the paused run after the user approves/denies a tool call. */
  const handleApprovalDecision = (callId: string, decision: 'approve' | 'deny') => {
    const nextDecisions = { ...decisions, [callId]: decision };
    setDecisions(nextDecisions);
    const remaining = pendingApprovals.filter((p) => p.call_id !== callId);
    setPendingApprovals(remaining);
    // Fire resume once every pending call has a decision.
    if (remaining.length === 0) {
      setDecisions(nextDecisions);
      void (async () => {
        if (isLoading) return;
        setIsLoading(true);
        setError(null);
        try {
          abortControllerRef.current = new AbortController();
          const approvalPayload = buildApprovalBody(autoApprove, nextDecisions);
          const response = await postChat(
            [...messages],
            approvalPayload,
            stream,
            abortControllerRef.current.signal,
          );
          if (!response.ok) {
            let errMessage = `HTTP error! Status: ${response.status}`;
            try {
              const errObj = await response.json();
              if (errObj.error?.message) errMessage = errObj.error.message;
            } catch {}
            throw new Error(errMessage);
          }
          if (stream) {
            await handleStreamResponse(response, abortControllerRef.current?.signal);
          } else {
            const data = await response.json();
            handleNonStreamingData(data);
          }
        } catch (err: any) {
          if (err.name !== 'AbortError') {
            console.error('Chat resume error:', err);
            setError(err.message || 'An error occurred while resuming after approval.');
          }
        } finally {
          setIsLoading(false);
        }
      })();
    }
  };

  const handleStreamResponse = async (response: Response, signal?: AbortSignal) => {
    const reader = response.body?.getReader();
    if (!reader) throw new Error('ReadableStream reader not available');

    const decoder = new TextDecoder('utf-8');
    let assistantMessageText = '';
    let assistantThinkingText = '';
    // Chars of assistantMessageText already painted. Burst arrivals are
    // revealed progressively (typewriter); small deltas paint immediately.
    let flushedContentLen = 0;
    // Accumulate delta.tool_calls by index: {index -> {id, name, args}}
    const toolCallParts = new Map<number, { id: string; name: string; args: string }>();

    const paintAssistant = (visibleLen: number) => {
      const snapshot = [...toolCallParts.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([, p], i) => ({
          id: p.id || `call_stream_${i}`,
          type: 'function',
          function: { name: p.name, arguments: p.args },
        }));
      const toolCallsSnapshot = snapshot.length > 0 ? snapshot : undefined;
      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0) {
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: assistantMessageText.slice(0, visibleLen),
            thinking: assistantThinkingText || undefined,
            ...(toolCallsSnapshot ? { tool_calls: toolCallsSnapshot } : {}),
          };
        }
        return updated;
      });
    };

    setMessages((prev) => [
      ...prev,
      {
        role: 'assistant',
        content: '',
        model: selectedModel,
        timestamp: nowStamp(),
      },
    ]);

    let buffer = '';
    let streamPendingApprovals: ChatToolCall[] | null = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      let batchDirty = false;

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;
        const dataStr = trimmed.substring(6);
        if (dataStr === '[DONE]') continue;

        try {
          const parsed = JSON.parse(dataStr);
          const choice = parsed.choices?.[0] ?? {};
          const delta = choice?.delta ?? {};
          const contentDelta = delta.content || '';
          let reasoningDelta = delta.reasoning || '';
          if (!reasoningDelta && Array.isArray(delta.reasoning_details)) {
            reasoningDelta = delta.reasoning_details.map((p: any) => p?.text || '').join('');
          }

          // Accumulate streaming tool calls (OpenAI chunk shape).
          const deltaToolCalls = delta.tool_calls;
          if (Array.isArray(deltaToolCalls)) {
            for (const tc of deltaToolCalls) {
              const idx: number = typeof tc?.index === 'number' ? tc.index : 0;
              const prevPart = toolCallParts.get(idx) ?? { id: '', name: '', args: '' };
              prevPart.id += String(tc?.id ?? '');
              prevPart.name += String(tc?.function?.name ?? tc?.name ?? '');
              prevPart.args += String(tc?.function?.arguments ?? tc?.arguments ?? '');
              toolCallParts.set(idx, prevPart);
            }
          }

          // Bridge may signal approval_required via a streamed finish_reason / payload.
          const finishReason: string | undefined = choice?.finish_reason;
          if (finishReason === 'approval_required') {
            const rawPending = choice?.pending_approvals ?? parsed?.pending_approvals ?? [];
            if (Array.isArray(rawPending) && rawPending.length > 0) {
              streamPendingApprovals = rawPending.map((p: any) => ({
                call_id: String(p?.call_id ?? p?.id ?? ''),
                name: String(p?.name ?? p?.function?.name ?? 'unknown_tool'),
                arguments: String(p?.arguments ?? p?.function?.arguments ?? ''),
              }));
            }
          }

          if (contentDelta) assistantMessageText += contentDelta;
          if (reasoningDelta) assistantThinkingText += reasoningDelta;

          if (contentDelta || reasoningDelta || Array.isArray(deltaToolCalls)) {
            batchDirty = true;
          }
        } catch {}
      }

      // Paint what arrived in this network read: small incremental deltas go
      // straight through; large single-read bursts are revealed progressively
      // so the message visibly streams instead of popping in all at once.
      if (batchDirty && !signal?.aborted) {
        const targetLen = assistantMessageText.length;
        if (targetLen - flushedContentLen > PACING_THRESHOLD_CHARS) {
          let n = flushedContentLen;
          while (n < targetLen) {
            if (signal?.aborted) return;
            n = nextRevealBoundary(assistantMessageText, n, PACING_SLICE_CHARS);
            paintAssistant(n);
            await sleep(PACING_FRAME_MS);
          }
        } else {
          paintAssistant(targetLen);
        }
        flushedContentLen = targetLen;
      }
    }

    // After stream ends: surface pending approvals if the bridge requested them.
    // In manual mode with streamed tool_calls but no explicit payload, derive
    // approvals from the accumulated calls so the user can still Accept/Deny.
    if (streamPendingApprovals && streamPendingApprovals.length > 0) {
      setPendingApprovals(streamPendingApprovals);
    } else if (toolCallParts.size > 0 && !autoApprove) {
      const derived: ChatToolCall[] = [...toolCallParts.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([, p], i) => ({
          call_id: p.id || `call_stream_${i}`,
          name: p.name || 'unknown_tool',
          arguments: p.args,
        }));
      setPendingApprovals(derived);
    }
  };

  const handleCancelRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  };

  const handleRegenerateLast = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (!lastUserMsg) return;

    // Drop last assistant response if exists
    setMessages((prev) => {
      if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
        return prev.slice(0, -1);
      }
      return prev;
    });

    handleSendMessage(undefined, lastUserMsg.content);
  };

  const renderMessageContent = (text: string) => {
    if (!text) return null;
    let escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const parts = escaped.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const codeLines = part.replace(/^```(\w*\n)?/, '').replace(/```$/, '');
        return <CodeBlock key={index} code={codeLines} />;
      }

      let renderedPart = part;
      renderedPart = renderedPart.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      renderedPart = renderedPart.replace(/\*([^*]+)\*/g, '<em>$1</em>');
      renderedPart = renderedPart.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-brand-500 font-mono text-xs">$1</code>');
      renderedPart = renderedPart.replace(/\n/g, '<br />');

      return <span key={index} dangerouslySetInnerHTML={{ __html: renderedPart }} />;
    });
  };

  return (
    <div className="flex gap-3.5 flex-1 min-h-0 w-full h-full relative">
      {/* Collapsible History Sidebar */}
      {showSidebar && (
        <aside className="w-64 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col p-4 shrink-0 space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold text-xs text-slate-900 dark:text-slate-100">
              <History className="w-4 h-4 text-brand-500" />
              <span>Chat History</span>
            </div>
            <button
              onClick={() => setShowSidebar(false)}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 text-xs font-semibold text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>

          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin">
            {sessions.map((s) => {
              const active = s.id === currentSessionId;
              return (
                <div
                  key={s.id}
                  onClick={() => switchSession(s)}
                  className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition-colors ${
                    active
                      ? 'bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 font-semibold border border-brand-200 dark:border-brand-900/50'
                      : 'hover:bg-slate-100 dark:hover:bg-slate-800/60 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{s.title}</span>
                  </div>
                  <button
                    onClick={(e) => deleteSession(s.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-opacity"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </aside>
      )}

      {/* Main Chat Content */}
      <div className="flex-1 space-y-3.5 flex flex-col min-h-0 w-full">
        {/* Settings/Control Bar */}
        <div className="p-3.5 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 shrink-0">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-[#121B2D] dark:hover:bg-slate-800/80 border border-slate-200 dark:border-slate-700 transition-colors"
              title="Toggle History Sidebar"
            >
              <PanelLeft className="w-4 h-4 text-slate-500" />
            </button>

            {/* Model Selector */}
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-slate-400" />
              <select
                id="model-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={isFetchingModels || filteredModels.length === 0}
                className="px-3 py-2 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 outline-none focus:border-brand-500 min-w-[200px]"
              >
                {isFetchingModels ? (
                  <option>Loading models...</option>
                ) : filteredModels.length === 0 ? (
                  <option>No matching models</option>
                ) : (
                  filteredModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))
                )}
              </select>
              <button
                onClick={fetchModels}
                disabled={isFetchingModels}
                title="Refresh models"
                className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-[#121B2D] dark:hover:bg-slate-800/80 border border-slate-200 dark:border-slate-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${isFetchingModels ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Model Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={modelSearch}
                onChange={(e) => setModelSearch(e.target.value)}
                placeholder="Search models..."
                className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500 w-32"
              />
            </div>

            {/* Stream Toggle */}
            <div className="flex items-center gap-2 select-none">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Stream</span>
              <button
                type="button"
                onClick={() => setStream(!stream)}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                  stream ? 'bg-slate-900 dark:bg-brand-600' : 'bg-slate-200 dark:bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    stream ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Agentic mode Toggle */}
            <div className="flex items-center gap-2 select-none" title="Agentic mode: let the AI call RakshakX tools (scan, findings, reports). OFF = plain chat.">
              <Sparkles className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Agentic</span>
              <button
                type="button"
                onClick={toggleAgenticMode}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                  agenticMode ? 'bg-slate-900 dark:bg-brand-600' : 'bg-slate-200 dark:bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    agenticMode ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Agentic approval Toggle */}
            <div className="flex items-center gap-2 select-none" title="Auto-approve tool calls in this chat">
              <Wrench className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Auto-approve</span>
              <button
                type="button"
                onClick={toggleAutoApprove}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                  autoApprove ? 'bg-slate-900 dark:bg-brand-600' : 'bg-slate-200 dark:bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    autoApprove ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {liveAgents.some((ag) => ag.status === 'running' || ag.status === 'executing_tool' || ag.status === 'thinking' || ag.status === 'waiting') && (
              <button
                type="button"
                onClick={() => setShowAgentsPanel(!showAgentsPanel)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                  showAgentsPanel
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-slate-50 dark:bg-[#121B2D] text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Agents ({liveAgents.filter((ag) => ag.status === 'running' || ag.status === 'executing_tool' || ag.status === 'thinking' || ag.status === 'waiting').length})</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setShowLogsConsole(!showLogsConsole)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                showLogsConsole
                  ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                  : 'bg-slate-50 dark:bg-[#121B2D] text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Live Logs</span>
            </button>

            <button
              onClick={exportCurrentChatMarkdown}
              title="Export Markdown"
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-[#121B2D] dark:hover:bg-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Collapsible Live System Logs Console inside Chat */}
        {showLogsConsole && (
          <div className="h-80 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 p-3 shadow-xs shrink-0 animate-fadeIn overflow-hidden flex flex-col">
            <LiveLogsConsole />
          </div>
        )}

        {/* Error Alert Box */}
        {error && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-300 text-xs flex gap-2 items-start shrink-0 animate-fadeIn">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {/* Messages Scroll Area */}
        <div className="flex-grow min-h-0 p-6 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col justify-between overflow-hidden">
          <div className="flex-1 overflow-y-auto space-y-6 pr-2 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-800 pb-4">
            {/* Live Active Subagents Monitor Banner */}
            {liveAgents.length > 0 && (
              <div className="mb-4">
                <InlineSubagentMonitor agents={liveAgents} defaultOpen={true} />
              </div>
            )}

            {messages.map((m, index) => {
              if (m.role === 'tool') return null; // Tool results are embedded inside assistant's ToolActivityBlock
              const isUser = m.role === 'user';
              // Collect the following tool-result message per call id for inline snippets.
              const resultSnippets: Record<string, string> = {};
              if (m.tool_calls) {
                for (const tc of m.tool_calls) {
                  const hit = messages.find(
                    (x) => x.role === 'tool' && x.tool_call_id === tc.id,
                  );
                  if (hit) resultSnippets[tc.id] = hit.content;
                }
              }
              const toolCallList =
                m.tool_calls?.map((tc) => ({
                  id: tc.id,
                  name: tc.function.name,
                  args: tc.function.arguments,
                })) ??
                (m.toolCalls?.map((tc) => ({ id: tc.id, name: tc.name, args: tc.args })) ?? []);
              return (
                <div
                  key={index}
                  className={`flex gap-3 max-w-[85%] sm:max-w-[78%] ${
                    isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
                  } animate-fadeIn`}
                >
                  <div
                    className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-white ${
                      isUser
                        ? 'bg-slate-900 dark:bg-brand-600'
                        : 'bg-brand-100 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400'
                    }`}
                  >
                    {isUser ? <span className="text-[10px] font-bold">ME</span> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className="space-y-1">
                    <div
                      className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                        isUser
                          ? 'bg-slate-950 text-slate-100 rounded-tr-none'
                          : 'bg-slate-50 dark:bg-[#121B2D] border border-slate-200/60 dark:border-slate-800/80 text-slate-800 dark:text-slate-200 rounded-tl-none'
                      }`}
                    >
                      {(() => {
                        if (isUser) return renderMessageContent(m.content);
                        const split = m.thinking ? null : splitThinking(m.content);
                        const thinking = m.thinking || split?.thinking;
                        const answer = m.thinking ? m.content : (split?.answer ?? m.content);
                        const streamingThis = isLoading && index === messages.length - 1;
                        const activeAgentsList = liveAgents.filter(
                          (ag) =>
                            ag.status === 'running' ||
                            ag.status === 'executing_tool' ||
                            ag.status === 'thinking' ||
                            ag.status === 'waiting'
                        );
                        return (
                          <>
                            {thinking && <ThinkingBlock thinking={thinking} defaultOpen={streamingThis} />}
                            {toolCallList.length > 0 && (
                              <ToolActivityBlock
                                calls={toolCallList}
                                resultSnippets={resultSnippets}
                                defaultOpen={streamingThis}
                              />
                            )}
                            {renderMessageContent(answer)}
                          </>
                        );
                      })()}

                      {!isUser && isLoading && index === messages.length - 1 && m.content === '' && (
                        <span className="inline-flex items-center gap-2 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                          <span className="inline-block w-1.5 h-4 bg-brand-500 animate-pulse" />
                          <span>Thinking… {thinkingSecs}s</span>
                        </span>
                      )}
                    </div>

                    <div className={`flex items-center gap-2 text-[9px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider ${isUser ? 'justify-end' : 'justify-start'}`}>
                      {m.model && <span>{m.model}</span>}
                      <span>·</span>
                      <span>{m.timestamp}</span>
                      {!isUser && !isLoading && index === messages.length - 1 && (
                        <button
                          onClick={handleRegenerateLast}
                          className="hover:text-brand-500 flex items-center gap-0.5 ml-2"
                          title="Regenerate Last Response"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Retry</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Pending Tool Approvals Banner */}
          {pendingApprovals.length > 0 && (
            <div className="mb-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 space-y-2 animate-fadeIn">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-400">
                <AlertTriangle className="w-4 h-4" />
                <span>Tool Execution Approval Required ({pendingApprovals.length})</span>
              </div>
              <div className="space-y-2">
                {pendingApprovals.map((p) => (
                  <div key={p.call_id} className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3 text-xs">
                    <div className="truncate font-mono">
                      <span className="font-bold text-amber-300">⚡ {p.name}</span>
                      {p.arguments && <span className="text-slate-400 text-[10px] ml-2">({p.arguments.slice(0, 60)}...)</span>}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleApprovalDecision(p.call_id, 'approve')}
                        className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] transition-colors shadow-xs"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApprovalDecision(p.call_id, 'deny')}
                        className="px-3 py-1 rounded bg-red-600 hover:bg-red-700 text-white font-bold text-[11px] transition-colors shadow-xs"
                      >
                        Deny
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Presets Bar */}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap gap-2 mb-2">
            {[
              '🛡️ Audit JWT Authentication',
              '💉 Test SQL Injection (Boolean Blind)',
              '🔍 Whitebox Code Security Audit',
              '📄 Generate CVSS Vulnerability Report',
            ].map((preset, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(undefined, preset)}
                disabled={isLoading}
                className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/60 hover:bg-slate-200 dark:hover:bg-slate-800 text-[11px] text-slate-600 dark:text-slate-300 font-medium transition-colors disabled:opacity-50"
              >
                {preset}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <form onSubmit={handleSendMessage} className="flex items-center gap-2 shrink-0">
            <div className="relative flex-1">
              <Terminal className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isLoading}
                placeholder={isLoading ? 'Assistant is generating response...' : 'Type your security query... (Press Enter to send)'}
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500 disabled:opacity-50"
              />
            </div>
            {isLoading ? (
              <button
                type="button"
                onClick={handleCancelRequest}
                className="px-4 py-3 rounded-xl font-bold text-xs sm:text-sm text-white bg-red-600 hover:bg-red-700 dark:bg-red-950/40 dark:text-red-300 border border-transparent dark:border-red-900/30 transition-colors flex items-center gap-1.5 shrink-0 shadow-xs"
              >
                <span>Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!inputValue.trim()}
                className="px-5 py-3 rounded-xl font-bold text-xs sm:text-sm text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 transition-colors flex items-center gap-1.5 shrink-0 disabled:opacity-50 disabled:cursor-not-allowed shadow-xs"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send</span>
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

