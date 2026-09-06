"""Terminal watchdog: poll the backend health endpoint and alert instantly.

Polls GET /api/agents/health every --interval seconds and prints a line per
agent. On a NEW stuck_suspected / stopped / degraded verdict it rings the
terminal bell + prints a highlighted ALERT so a stuck scan is noticed
immediately without staring at the UI.

Usage:
    .venv/bin/python scripts/watch_scan.py
    .venv/bin/python scripts/watch_scan.py --interval 5 --backend http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

BAD = ("stopped", "stuck_suspected", "degraded")


def fetch_health(backend: str, timeout: float) -> dict | None:
    try:
        with urllib.request.urlopen(f"{backend}/api/agents/health", timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as exc:
        print(f"[watch] backend unreachable: {exc}", flush=True)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="RakshakX scan watchdog (terminal alerts)")
    ap.add_argument("--interval", type=float, default=5.0, help="poll interval seconds")
    ap.add_argument("--backend", default="http://127.0.0.1:8080", help="backend base URL")
    args = ap.parse_args()

    print(f"[watch] polling {args.backend}/api/agents/health every {args.interval}s — Ctrl+C to stop", flush=True)
    known_bad: set[str] = set()
    while True:
        data = fetch_health(args.backend, timeout=10)
        if data:
            ts = time.strftime("%H:%M:%S")
            for agent in data.get("agents", []):
                verdict = agent.get("verdict", "?")
                key = f"{agent.get('id')}:{verdict}"
                line = (
                    f"[{ts}] {agent.get('name')} turn={agent.get('turns')} "
                    f"verdict={verdict} hb_ago={agent.get('seconds_since_heartbeat')}s :: {agent.get('detail')}"
                )
                if verdict in BAD:
                    if key not in known_bad:
                        # Terminal bell + alert for NEWLY bad agents only.
                        print("\a" + f"!!! ALERT {line}", flush=True)
                    else:
                        print(f"!!! STILL {line}", flush=True)
                    known_bad.add(key)
                elif verdict == "idle":
                    print(f"[...] SLOW {line}", flush=True)
                else:
                    print(f"[ok] {line}", flush=True)
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[watch] stopped.", flush=True)
            return 0


if __name__ == "__main__":
    sys.exit(main())
