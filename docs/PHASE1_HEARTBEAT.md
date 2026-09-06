# Phase 1 — Heartbeat Harness (heartbeat kabhi ruke nahi)

## Problem
Lambi tool executions (ffuf, nmap) ke dauran agent heartbeat stale ho jata tha →
UI watchdog false `stuck_suspected` bajata tha, jabki agent bilkul healthy tha.

## Root cause
`container.exec_run()` **sync/blocking** hai aur async event-loop thread me chalta tha.
Jab tak exec chal raha tha, loop freeze → 3-sec ticker task chal hi nahi pata tha.

## Fix (3 edits + 1 doc)
1. `rakshak/runtime/sdk_session.py` — blocking `exec_command` + `container.reload()`
   ab `asyncio.to_thread()` me (loop free, ticker har 3s tick karega).
2. `rakshak/core/agents.py` + `execution.py` — naya `heartbeat_scope`
   (ContextVar: concurrent specialists me bhi sahi attribution); exec start pe
   `meta["exec"]` me 120-char command publish, turn-end pe clear.
   `touch_heartbeat(..., exec_detail)` — set / `""`=clear / `None`=untouched.
3. `rakshak/interface/viewer/agent_health.py` — health detail me `:: <command>`
   suffix + `exec` field; thresholds 60/180 **same rakhe** (tuning note in code).
   Healthy agent har 3s tick karta hai, to 180s silence = genuine stuck.

## Deviation from plan
Plan me threshold 300s se align karna tha — nahi kiya. Ticker fix ke baad
threshold badhana sirf real stuck detection slow karta.

## Proof
- `tests/test_heartbeat_harness.py` — 9/9 (ticker-keeps-ticking, truncation,
  clear semantics, scope isolation, health passthrough, to_thread).
- E2E real Docker: 60s `sleep` me max heartbeat gap **4.01s** (purana ~60s),
  `exec: "sleep 60"` UI field me, exit 0.
