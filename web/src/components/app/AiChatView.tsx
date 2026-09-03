import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, Sparkles, Terminal, Trash2, Cpu, RefreshCw, AlertTriangle, Search } from 'lucide-react';

interface Model {
  id: string;
  owned_by: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  timestamp: string;
}

export const AiChatView: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelSearch, setModelSearch] = useState('');
  const [showFreeOnly, setShowFreeOnly] = useState(true);
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
  const [error, setError] = useState<string | null>(null);
  const [isFetchingModels, setIsFetchingModels] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const API_BASE_URL = '';

  // Compute filtered models
  const filteredModels = models.filter(m => {
    const matchesSearch = m.id.toLowerCase().includes(modelSearch.toLowerCase());
    const isFree = m.id.includes('-free') || m.id === 'oc/big-pickle';
    const matchesFree = !showFreeOnly || isFree;
    return matchesSearch && matchesFree;
  });

  // Fetch models on component mount
  useEffect(() => {
    fetchModels();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Auto scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-select first filtered model if currently selected is filtered out
  useEffect(() => {
    if (filteredModels.length > 0 && !filteredModels.some(m => m.id === selectedModel)) {
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
        // Default to a free model if available
        const defaultModel = data.data.find((m: Model) => m.id === 'oc/nemotron-3.5-lightning-free' || m.id.includes('-free'))?.id || data.data[0]?.id || '';
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

  const parseErrorMessage = (rawMessage: string): string => {
    try {
      const jsonStart = rawMessage.indexOf('{');
      if (jsonStart !== -1) {
        const jsonPart = rawMessage.substring(jsonStart);
        const parsed = JSON.parse(jsonPart);
        if (parsed.error?.message) {
          return parsed.error.message;
        }
        if (parsed.message) {
          return parsed.message;
        }
      }
    } catch {
      // ignore
    }
    return rawMessage;
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    if (!selectedModel) {
      setError('Please select a model from the list.');
      return;
    }

    setError(null);
    const userMessageText = inputValue.trim();
    setInputValue('');

    const newMessages: Message[] = [
      ...messages,
      {
        role: 'user',
        content: userMessageText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];

    setMessages(newMessages);
    setIsLoading(true);

    try {
      abortControllerRef.current = new AbortController();

      const requestBody = {
        model: selectedModel,
        messages: newMessages.map(m => ({ role: m.role, content: m.content })),
        stream: stream,
      };

      const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        let errMessage = `HTTP error! Status: ${response.status}`;
        try {
          const errObj = await response.json();
          if (errObj.error?.message) {
            errMessage = errObj.error.message;
          }
        } catch {
          // ignore parsing error
        }
        throw new Error(errMessage);
      }

      if (stream) {
        await handleStreamResponse(response);
      } else {
        const data = await response.json();
        const assistantText = data.choices?.[0]?.message?.content || '';
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: assistantText,
            model: selectedModel,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Chat error:', err);
        setError(parseErrorMessage(err.message || 'An error occurred while generating response.'));
        // Remove empty assistant placeholder bubble if it exists
        setMessages(prev => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].role === 'assistant' && updated[updated.length - 1].content === '') {
            updated.pop();
          }
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleStreamResponse = async (response: Response) => {
    const reader = response.body?.getReader();
    if (!reader) throw new Error('ReadableStream reader not available');

    const decoder = new TextDecoder('utf-8');
    let assistantMessageText = '';
    
    // Add placeholder assistant message
    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        content: '',
        model: selectedModel,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;

        const dataStr = trimmed.substring(6);
        if (dataStr === '[DONE]') continue;

        try {
          const parsed = JSON.parse(dataStr);
          const delta = parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.delta?.reasoning || '';
          if (delta) {
            assistantMessageText += delta;
            setMessages(prev => {
              const updated = [...prev];
              if (updated.length > 0) {
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: assistantMessageText,
                };
              }
              return updated;
            });
          }
        } catch {
          // ignore parsing chunks error
        }
      }
    }
  };

  const handleCancelRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
      // Remove empty assistant placeholder bubble if it exists
      setMessages(prev => {
        const updated = [...prev];
        if (updated.length > 0 && updated[updated.length - 1].role === 'assistant' && updated[updated.length - 1].content === '') {
          updated.pop();
        }
        return updated;
      });
    }
  };

  const handleClearHistory = () => {
    if (isLoading) {
      handleCancelRequest();
    }
    if (window.confirm('Are you sure you want to clear your conversation history?')) {
      setMessages([
        {
          role: 'assistant',
          content: 'Hello! I am RakshakX Security Assistant. Select an AI model and ask me anything about code security, vulnerability patching, or penetration testing.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      setError(null);
    }
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    if (isLoading) {
      handleCancelRequest();
    }
  };

  // Listen for Escape key to abort request
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isLoading) {
        handleCancelRequest();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isLoading]);

  // Simple Markdown parsing function for TSX rendering
  const renderMessageContent = (text: string) => {
    if (!text) return null;

    // Escaping simple HTML entities
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Helper regex patterns
    const parts = escaped.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        // Code Block
        const codeLines = part.replace(/^```(\w*\n)?/, '').replace(/```$/, '');
        return (
          <pre key={index} className="my-3 p-4 rounded-xl bg-slate-950 text-slate-100 border border-slate-800 font-mono text-xs overflow-x-auto select-text">
            <code>{codeLines}</code>
          </pre>
        );
      }

      // Inline formatting (bold, italic, inline code)
      let renderedPart = part;
      // Bold
      renderedPart = renderedPart.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      // Italic
      renderedPart = renderedPart.replace(/\*([^*]+)\*/g, '<em>$1</em>');
      // Inline Code
      renderedPart = renderedPart.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-brand-500 font-mono text-xs">$1</code>');
      // Newlines
      renderedPart = renderedPart.replace(/\n/g, '<br />');

      return (
        <span
          key={index}
          dangerouslySetInnerHTML={{ __html: renderedPart }}
        />
      );
    });
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto flex flex-col flex-1 min-h-0 w-full">
      {/* Settings/Control Bar */}
      <div className="p-4 rounded-2xl bg-white dark:bg-[#0E1524] border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
        <div className="flex flex-wrap items-center gap-4">
          {/* Model Selector */}
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-slate-400" />
            <select
              id="model-select"
              value={selectedModel}
              onChange={handleModelChange}
              disabled={isFetchingModels || filteredModels.length === 0}
              className="px-3 py-2 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 outline-none focus:border-brand-500 min-w-[220px]"
            >
              {isFetchingModels ? (
                <option>Loading models...</option>
              ) : filteredModels.length === 0 ? (
                <option>No matching models</option>
              ) : (
                filteredModels.map(m => (
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

          {/* Model Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={modelSearch}
              onChange={(e) => setModelSearch(e.target.value)}
              placeholder="Search models..."
              className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-50 dark:bg-[#121B2D] border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:border-brand-500 w-36"
            />
          </div>

          {/* Free Filter Toggle */}
          <div className="flex items-center gap-2 select-none">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Free Only</span>
            <button
              type="button"
              onClick={() => setShowFreeOnly(!showFreeOnly)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                showFreeOnly ? 'bg-slate-900 dark:bg-brand-600' : 'bg-slate-200 dark:bg-slate-700'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                  showFreeOnly ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Stream Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Stream Responses</span>
            <button
              type="button"
              onClick={() => setStream(!stream)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                stream ? 'bg-slate-900 dark:bg-brand-600' : 'bg-slate-200 dark:bg-slate-700'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                  stream ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div>
          <button
            type="button"
            onClick={handleClearHistory}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-[#121B2D] dark:hover:bg-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear History</span>
          </button>
        </div>
      </div>

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
          {messages.map((m, index) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={index}
                className={`flex gap-3 max-w-[85%] sm:max-w-[75%] ${
                  isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
                } animate-fadeIn`}
              >
                {/* Avatar Icon */}
                <div
                  className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-white ${
                    isUser
                      ? 'bg-slate-900 dark:bg-brand-600'
                      : 'bg-brand-100 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400'
                  }`}
                >
                  {isUser ? (
                    <span className="text-[10px] font-bold">ME</span>
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>

                {/* Message Bubble */}
                <div className="space-y-1">
                  <div
                    className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? 'bg-slate-950 text-slate-100 rounded-tr-none'
                        : 'bg-slate-50 dark:bg-[#121B2D] border border-slate-200/60 dark:border-slate-800/80 text-slate-800 dark:text-slate-200 rounded-tl-none'
                    }`}
                  >
                    {renderMessageContent(m.content)}

                    {/* Cursor typing blinking indicator */}
                    {!isUser && isLoading && index === messages.length - 1 && m.content === '' && (
                      <span className="inline-block w-1.5 h-4 ml-1 bg-brand-500 animate-pulse" />
                    )}
                  </div>
                  
                  {/* Metadata under bubble */}
                  <div className={`flex items-center gap-1.5 text-[9px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider ${isUser ? 'justify-end' : 'justify-start'}`}>
                    {m.model && (
                      <>
                        <span>{m.model}</span>
                        <span>·</span>
                      </>
                    )}
                    <span>{m.timestamp}</span>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Assistant Bouncing Typing Dots (only shown before stream starts outputting) */}
          {isLoading && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex gap-3 max-w-[75%] mr-auto items-center animate-fadeIn">
              <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center bg-brand-100 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400">
                <Bot className="w-4 h-4" />
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-none bg-slate-50 dark:bg-[#121B2D] border border-slate-200/60 dark:border-slate-800/80 flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce duration-1000" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce duration-1000" style={{ animationDelay: '200ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce duration-1000" style={{ animationDelay: '400ms' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSendMessage} className="mt-4 pt-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center gap-2 shrink-0">
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
  );
};
