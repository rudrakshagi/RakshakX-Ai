import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Clock, Volume2, VolumeX, X } from 'lucide-react';

interface AttentionItem {
  id: string;
  name: string;
  verdict: string;
  detail: string;
}

const BAD_VERDICTS = new Set(['stuck_suspected', 'stopped', 'degraded']);

// Short double-beep via WebAudio — no asset file needed.
function beep() {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    [0, 0.22].forEach((delay, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = i === 0 ? 880 : 660;
      const t = ctx.currentTime + delay;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.25, t + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
      osc.start(t);
      osc.stop(t + 0.22);
    });
    setTimeout(() => void ctx.close(), 600);
  } catch {
    /* audio blocked before first user gesture — skip silently */
  }
}

function notify(title: string, body: string) {
  try {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') {
      new Notification(title, { body });
    } else if (Notification.permission === 'default') {
      void Notification.requestPermission().then((p) => {
        if (p === 'granted') new Notification(title, { body });
      });
    }
  } catch {
    /* notifications unavailable — banner still shows */
  }
}

/**
 * Global 5s watchdog strip rendered in AppLayout, visible on EVERY tab.
 * Previously stuck/degraded alerts only appeared inside Agent Topology,
 * so a user sitting on Logs/Dashboard never noticed. This polls
 * /api/agents/health continuously, shows a persistent banner, and fires
 * an audible + desktop notification exactly once per newly-bad agent.
 */
export const GlobalWatchdogBar: React.FC = () => {
  const [attention, setAttention] = useState<AttentionItem[]>([]);
  const [watch, setWatch] = useState<AttentionItem[]>([]);
  const [muted, setMuted] = useState(false);
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});
  const badIdsRef = useRef<Set<string>>(new Set());
  const mutedRef = useRef(false);
  mutedRef.current = muted;

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch('/api/agents/health');
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        const summary = data.summary || {};
        const attn: AttentionItem[] = (summary.attention || []).filter(
          (a: AttentionItem) => BAD_VERDICTS.has(a.verdict),
        );
        const idle: AttentionItem[] = summary.watch || [];
        setAttention(attn.filter((a) => !dismissed[a.id]));
        setWatch(idle);

        // Fire beep + desktop notification only for NEWLY bad agents.
        const prev = badIdsRef.current;
        const next = new Set(attn.map((a) => a.id));
        const fresh = attn.filter((a) => !prev.has(a.id));
        badIdsRef.current = next;
        if (fresh.length > 0) {
          const label = fresh.map((a) => `${a.name}: ${a.verdict}`).join(', ');
          if (!mutedRef.current) beep();
          notify('RakshakX agent needs attention', `${label}\n${fresh[0].detail}`);
        }
      } catch {
        /* backend down — stay silent, topology view reports it */
      }
    }
    poll();
    const interval = setInterval(poll, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [dismissed]);

  if (attention.length === 0 && watch.length === 0) return null;

  return (
    <div className="shrink-0">
      {attention.length > 0 && (
        <div className="px-6 py-2 bg-orange-500 dark:bg-orange-600 text-white flex items-center gap-2.5 text-xs font-semibold">
          <AlertTriangle className="w-4 h-4 shrink-0 animate-pulse" />
          <span className="flex-1 truncate">
            WATCHDOG: {attention.map((a) => `${a.name} (${a.verdict})`).join(', ')} — {attention[0].detail}
          </span>
          <button
            onClick={() => setMuted((m) => !m)}
            title={muted ? 'Unmute alert sound' : 'Mute alert sound'}
            className="p-1 rounded hover:bg-white/20 transition-colors"
          >
            {muted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={() => setDismissed((d) => ({ ...d, ...Object.fromEntries(attention.map((a) => [a.id, true])) }))}
            title="Dismiss until verdict clears"
            className="p-1 rounded hover:bg-white/20 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
      {attention.length === 0 && watch.length > 0 && !dismissed['slowing_bar'] && (
        <div className="px-6 py-1.5 bg-amber-100 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-900/50 text-amber-800 dark:text-amber-300 flex items-center gap-2 text-[11px] font-mono">
          <Clock className="w-3.5 h-3.5 shrink-0 text-amber-500" />
          <span className="flex-1 truncate">
            Slowing: {watch.map((a) => `${a.name} — ${a.detail}`).join(' · ')}
          </span>
          <button
            onClick={() => setDismissed((d) => ({ ...d, slowing_bar: true }))}
            title="Dismiss notification"
            className="p-1 rounded hover:bg-amber-200/50 dark:hover:bg-amber-900/50 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
