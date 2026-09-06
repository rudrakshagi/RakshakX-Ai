"""Agent liveness verdicts for the 5-second UI watchdog.

Pure functions over the persisted ``agents.json`` snapshot shape
(``{names, statuses, metadata, wait_kinds, errors, budget_stopped, ...}``),
so they are unit-testable without a running scan and reusable by both the
viewer ``GET /api/agents/health`` endpoint and offline diagnostics.

Verdicts:
- ``stopped``  — agent hit a terminal failure (failed/crashed). Needs attention.
- ``finished`` — agent completed/stopped normally. Nothing to do.
- ``paused``   — scan-wide budget stop/pause. Waiting on operator/budget.
- ``waiting``  — parked on child agents or user input. Alive, not turning.
- ``running``  — heartbeat fresh, turning normally.
- ``degraded`` — turning but piling up consecutive errors.
- ``idle``     — status says running but no heartbeat for a while (early
  warning, below the stuck threshold). Worth a glance, not an alarm yet.
- ``stuck_suspected`` — status says running but no heartbeat for a while.
- ``unknown``  — running but no heartbeat recorded yet (just spawned / old run).
"""

from __future__ import annotations

import time
from typing import Any

# Thresholds (seconds). Rate-limit backoff alone can idle an agent ~65s and a
# single LLM turn can take minutes, so "stuck" must be well above that. The
# *check* runs every 5s; these are *verdict* thresholds, not the interval.
# WARN_AFTER_S fires the soft "idle" early-warning so operators see a slowing
# agent long before it is declared stuck.
# NOTE (heartbeat-harness): thresholds stay BELOW the 300s exec cap on
# purpose. Sandbox exec runs via asyncio.to_thread + a 3s heartbeat ticker,
# so any healthy agent — even mid-ffuf — refreshes last_heartbeat every ~3s.
# A 180s+ silence therefore means the loop itself is wedged (genuine stuck),
# never "long tool still running". Do NOT raise STUCK_AFTER_S to cover exec
# time; that would only delay real stuck detection.
WARN_AFTER_S = 60.0
STUCK_AFTER_S = 180.0
DEGRADED_ERRORS = 3


def compute_agent_health(
    state: dict[str, Any],
    *,
    now: float | None = None,
    stuck_after_s: float = STUCK_AFTER_S,
    warn_after_s: float = WARN_AFTER_S,
) -> list[dict[str, Any]]:
    """Compute a per-agent liveness verdict list from an agents.json snapshot."""
    at = time.time() if now is None else float(now)
    names: dict[str, Any] = state.get("names", {}) or {}
    statuses: dict[str, Any] = state.get("statuses", {}) or {}
    metadata: dict[str, Any] = state.get("metadata", {}) or {}
    wait_kinds: dict[str, Any] = state.get("wait_kinds", {}) or {}
    errors: dict[str, Any] = state.get("errors", {}) or {}
    budget_stopped = bool(state.get("budget_stopped", False))
    budget_paused = bool(state.get("budget_paused", False))

    report: list[dict[str, Any]] = []
    for agent_id, name in names.items():
        status = str(statuses.get(agent_id, "unknown"))
        meta = metadata.get(agent_id, {}) or {}
        last_hb = meta.get("last_heartbeat")
        try:
            age = at - float(last_hb) if last_hb is not None else None
        except (TypeError, ValueError):
            age = None
        try:
            consec_errs = int(meta.get("consecutive_errors", 0) or 0)
        except (TypeError, ValueError):
            consec_errs = 0

        if status in ("failed", "crashed"):
            verdict, detail = "stopped", str(errors.get(agent_id, status))
        elif status in ("completed", "stopped"):
            verdict, detail = "finished", f"terminal state: {status}"
        elif budget_stopped or budget_paused or status == "budget_paused":
            verdict, detail = "paused", "scan budget stop/pause active"
        elif status == "waiting":
            wk = str(wait_kinds.get(agent_id, "agents"))
            verdict, detail = "waiting", f"parked, waiting on: {wk}"
        elif status == "running":
            if consec_errs >= DEGRADED_ERRORS:
                verdict = "degraded"
                detail = f"{consec_errs} consecutive turn errors"
            elif age is None:
                verdict, detail = "unknown", "no heartbeat recorded yet"
            elif age > stuck_after_s:
                verdict = "stuck_suspected"
                detail = f"no turn progress for {int(age)}s (last phase: {meta.get('phase', '?')})"
            elif age > warn_after_s:
                verdict = "idle"
                detail = f"no heartbeat for {int(age)}s, turn {meta.get('turns', 0)} (phase: {meta.get('phase', '?')}) — slowing, not stuck yet"
            else:
                verdict = "running"
                detail = f"turn {meta.get('turns', 0)} alive {int(age)}s ago (phase: {meta.get('phase', '?')})"
            # Surface the currently-executing sandbox command (if published
            # by sdk_session) so the operator sees WHAT is running.
            exec_cmd = str(meta.get("exec") or "").strip()
            if exec_cmd:
                detail = f"{detail} :: {exec_cmd}"
        else:
            verdict, detail = "unknown", f"unrecognized status: {status}"

        report.append({
            "id": agent_id,
            "name": name,
            "status": status,
            "verdict": verdict,
            "detail": detail,
            "seconds_since_heartbeat": None if age is None else round(age, 1),
            "turns": meta.get("turns", 0),
            "phase": meta.get("phase"),
            "exec": meta.get("exec"),
            "consecutive_errors": consec_errs,
        })
    return report


def summarize_health(report: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll per-agent verdicts into counts + needs-attention flag."""
    counts: dict[str, int] = {}
    bad = [a for a in report if a["verdict"] in ("stopped", "stuck_suspected", "degraded")]
    early = [a for a in report if a["verdict"] == "idle"]
    for entry in report:
        counts[entry["verdict"]] = counts.get(entry["verdict"], 0) + 1
    return {
        "total": len(report),
        "counts": counts,
        "needs_attention": len(bad) > 0,
        "attention": [{"id": a["id"], "name": a["name"], "verdict": a["verdict"], "detail": a["detail"]} for a in bad],
        "early_warning": len(early) > 0,
        "watch": [{"id": a["id"], "name": a["name"], "verdict": a["verdict"], "detail": a["detail"]} for a in early],
    }
