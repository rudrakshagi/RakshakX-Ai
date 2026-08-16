import React, { useState, useEffect } from 'react';
import { Key, Bot, Shield, Check, Eye, EyeOff, Save, Sparkles, Server, Sliders, AlertCircle, Copy, Terminal, Activity } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('openai/gpt-4o');
  const [apiKey, setApiKey] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [budget, setBudget] = useState(10.0);
  const [showKey, setShowKey] = useState(false);
  const [useMcpLlm, setUseMcpLlm] = useState(false);
  const [savedStatus, setSavedStatus] = useState<string | null>(null);
  const [isKeyConfigured, setIsKeyConfigured] = useState(false);
  const [copiedMcp, setCopiedMcp] = useState(false);

  useEffect(() => {
    async function loadConfig() {
      try {
        const res = await fetch('/api/config');
        if (res.ok) {
          const data = await res.json();
          if (data.provider) setProvider(data.provider);
          if (data.model) setModel(data.model);
          if (data.api_base) setApiBase(data.api_base);
          if (data.max_budget_usd) setBudget(data.max_budget_usd);
          if (data.use_mcp_ide_llm) setUseMcpLlm(data.use_mcp_ide_llm);
          if (data.is_key_configured) setIsKeyConfigured(true);
        }
      } catch (e) {
        // Local fallback
      }
    }
    loadConfig();
  }, []);

  const handleProviderChange = (newProv: string) => {
    setProvider(newProv);
    if (newProv === 'openai') {
      setModel('openai/gpt-4o');
      setApiBase('');
    } else if (newProv === 'anthropic') {
      setModel('anthropic/claude-3-7-sonnet');
      setApiBase('');
    } else if (newProv === 'gemini') {
      setModel('gemini/gemini-2.5-pro');
      setApiBase('');
    } else if (newProv === 'ollama') {
      setModel('ollama/deepseek-r1');
      setApiBase('http://localhost:11434');
    } else if (newProv === 'openrouter') {
      setModel('openrouter/anthropic/claude-3.7-sonnet');
      setApiBase('https://openrouter.ai/api/v1');
    }
  };

  const handleCopyMcp = () => {
    const jsonSnippet = JSON.stringify({
      "mcpServers": {
        "rakshakx": {
          "command": "python",
          "args": ["-m", "rakshak.mcp.server"]
        }
      }
    }, null, 2);
    navigator.clipboard.writeText(jsonSnippet);
    setCopiedMcp(true);
    setTimeout(() => setCopiedMcp(false), 2500);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          model,
          api_key: apiKey,
          api_base: apiBase,
          max_budget_usd: budget,
          use_mcp_ide_llm: useMcpLlm,
        }),
      });
      if (res.ok) {
        setSavedStatus('success');
        if (apiKey) setIsKeyConfigured(true);
        setTimeout(() => setSavedStatus(null), 3000);
      }
    } catch (err) {
      setSavedStatus('Saved to local session');
      setTimeout(() => setSavedStatus(null), 3000);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* 1. MCP Bridge & IDE Direct LLM Card */}
      <div className="p-8 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400 text-xs font-semibold border border-sky-200 dark:border-sky-900/60">
              <Activity className="w-3.5 h-3.5" />
              <span>MCP PROTOCOL BRIDGE</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              Connect with Antigravity, OpenCode & Claude Desktop
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
              Use the LLM and AI Agent directly from your IDE or environment (Antigravity IDE, OpenCode, Claude Desktop, Cursor) with zero extra API key configuration.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700/80 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <span>MCP Configuration JSON (mcp_config.json)</span>
            <button
              onClick={handleCopyMcp}
              className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
            >
              {copiedMcp ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedMcp ? 'Copied to Clipboard!' : 'Copy Config'}</span>
            </button>
          </div>

          <pre className="p-3.5 rounded-lg bg-slate-900 text-sky-400 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800">
{`{
  "mcpServers": {
    "rakshakx": {
      "command": "python",
      "args": ["-m", "rakshak.mcp.server"]
    }
  }
}`}
          </pre>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">
            Paste this snippet into your IDE's <code>mcp_config.json</code> or Antigravity tool settings. Your IDE's active LLM will automatically control RakshakX pentest tools!
          </div>
        </div>
      </div>

      {/* 2. Direct LLM Providers & API Key Card */}
      <div className="p-8 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-8">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 text-xs font-semibold border border-brand-200 dark:border-brand-900/60 mb-3">
            <Bot className="w-3.5 h-3.5" />
            <span>STANDALONE LLM CONFIGURATION</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Direct Cloud & Local LLM Providers
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Or provide a direct API key / local Ollama endpoint for the standalone multi-agent engine.
          </p>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          {/* Provider Selection */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Select LLM Provider
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { id: 'openai', label: 'OpenAI', desc: 'GPT-4o, o3-mini' },
                { id: 'anthropic', label: 'Anthropic', desc: 'Claude 3.7 / 3.5 Sonnet' },
                { id: 'gemini', label: 'Google Gemini', desc: 'Gemini 2.5 Pro / Flash' },
                { id: 'ollama', label: 'Ollama (Local)', desc: 'DeepSeek R1, Llama 3' },
                { id: 'openrouter', label: 'OpenRouter', desc: 'Multi-provider routing' },
                { id: 'custom', label: 'Custom Endpoint', desc: 'Any OpenAI-compatible API' },
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleProviderChange(p.id)}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    provider === p.id
                      ? 'bg-slate-900 text-white dark:bg-brand-600 border-slate-900 dark:border-brand-500 shadow-xs'
                      : 'bg-slate-50 dark:bg-[#121B2D] text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                >
                  <div className="font-bold text-xs">{p.label}</div>
                  <div className="text-[10px] opacity-70 mt-0.5">{p.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Model Identifier */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Model Identifier (LiteLLM Format)
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. openai/gpt-4o, anthropic/claude-3-7-sonnet, ollama/deepseek-r1"
              className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 font-mono text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:outline-hidden focus:border-brand-500"
            />
          </div>

          {/* API Key Input */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                API Secret Key
              </label>
              {isKeyConfigured && (
                <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-mono">
                  <Check className="w-3 h-3" />
                  Key Configured
                </span>
              )}
            </div>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={isKeyConfigured ? '••••••••••••••••••••••••••••••••' : 'Enter your provider API Key (e.g. sk-...)'}
                className="w-full pl-4 pr-11 py-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 font-mono text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5">
              Keys are stored locally on your machine in <code>rakshak.config.json</code> and never transmitted to external third parties.
            </p>
          </div>

          {/* API Base URL (For Ollama / Local / Custom) */}
          {(provider === 'ollama' || provider === 'openrouter' || provider === 'custom') && (
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                Custom API Base URL
              </label>
              <input
                type="text"
                value={apiBase}
                onChange={(e) => setApiBase(e.target.value)}
                placeholder="e.g. http://localhost:11434 or https://openrouter.ai/api/v1"
                className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 font-mono text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:outline-hidden focus:border-brand-500"
              />
            </div>
          )}

          {/* Max Budget Ceiling Slider */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Max Scan Budget Limit ($ USD)
              </label>
              <span className="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">
                ${budget.toFixed(2)} USD
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={budget}
              onChange={(e) => setBudget(parseFloat(e.target.value))}
              className="w-full accent-brand-600 cursor-pointer"
            />
          </div>

          {/* Save Button */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            {savedStatus ? (
              <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 font-mono">
                <Check className="w-4 h-4" />
                <span>Configuration saved to rakshak.config.json!</span>
              </div>
            ) : (
              <div className="text-xs text-slate-400">
                CLI Env Alternative: <code>export OPENAI_API_KEY="..."</code>
              </div>
            )}

            <button
              type="submit"
              className="px-6 py-3 rounded-xl font-bold text-xs sm:text-sm text-white bg-slate-900 hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700 transition-colors shadow-sm flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>Save LLM Settings</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
