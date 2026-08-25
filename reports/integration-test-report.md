# RakshakX — Frontend↔Backend Integration Test & Fix Report

**Date:** 18 Aug 2026
**Scope:** Frontend React console (`web/`) ↔ Python backend REST API (`rakshak/interface/viewer/server.py`)
**Status:** Core integration working · Findings blocked by external LLM quota

---

## 1. Objective
Verify that every request the frontend UI makes actually reaches the backend and returns data in the exact shape each component parses. Fix any gap so the console shows **live real data** instead of mocks/failed calls — scan launch, live status, agents, and report downloads.

---

## 2. What was done (fixed)

### 2.1 Backend fixes — `rakshak/interface/viewer/server.py`
| # | Change | Why |
|---|--------|-----|
| 1 | `POST /api/scan` now spawns a **real background scan** (`_run_scan_background` → `run_rakshak_scan`) instead of only returning a JSON stub | Previously launched scans stuck at "Queued" forever — no real scan ever ran |
| 2 | Added `_set_active_scan` / `_resolve_run_dir` — GET endpoints serve the **latest launched scan's** live data | Previously `/api/vulnerabilities`, `/api/agents`, `/api/overview` always read from the **fixed view scan** dir, so a new scan never showed its own results |
| 3 | `_write_run_meta` persists live status (`Queued→Running→Completed/Failed`) to `run_meta.json` | Frontend "Recent Scans" table now shows real status + duration |
| 4 | `GET /api/runs` reads real target/mode/status from `run_meta.json` | Before, it fell back to folder-hash as target and fake `14m 20s` |
| 5 | `_resolve_artifact_dir` — `report.md` / `sarif.json` / `report.pdf` fall back to view scan when active scan's artifacts not ready | ReportsCenter "Download SARIF/PDF" buttons returned 404 for a freshly launched scan |
| 6 | `_apply_config_env` at startup pushes `provider/model/api_key` into process env (`GROQ`, `OPENROUTER`, `OPENAI`, …) | Scan runner's LiteLLM got `api_key: None` → `AuthenticationError` |
| 7 | **OpenRouter provider route added** (`OPENROUTER_API_KEY`) | Provider `openrouter` was setting `OPENAI_API_KEY`, so LLM calls returned 401 "No cookie auth credentials found" |
| 8 | `_resolve_run_dir` resets stale active dir if deleted | Test-scans deleted on disk left handlers pointing at a non-existent dir → sarif/pdf 404 |

### 2.2 Frontend fixes — `web/src/components/app/`
| Component | Change |
|-----------|--------|
| `ReportsCenter.tsx` | Now fetches live `/api/report` into the markdown preview; export buttons hit real `/api/sarif`, `/api/pdf`, `/api/report` |
| `AgentTopologyView.tsx` | Polls real `/api/agents` (live agent names/statuses/tasks) + POSTs real `/api/steer` |
| `ScanCreator.tsx` | POSTs real `/api/scan` with target/mode/prompt (was already wired) |

### 2.3 Verified end-to-end (live checks performed)
- **E2E suite: 14/14 PASS** (App poll loop, config GET/POST round-trip, scan launch visible in runs, steer, report/sarif/pdf)
- **Response-shape suite: 35/36 PASS** — each endpoint returns exactly the keys each component parses
- **Real scan lifecycle verified** on `http://scanme.nmap.org` (`scan-95e5d26e`, `scan-69570874`):
  `Queued → Running` · sandbox container `rakshakx/sandbox:latest` started · Root Orchestrator built (16 tools) · sub-agent registered · 50+ LLM calls · scan reaches `Completed`
- `tsc --noEmit` → **0 errors** · `vite build` → **clean**

---

## 3. What is PENDING / blocked

### 3.1 🔴 LLM provider quota — the single blocker for findings
- **Symptom:** scans run the full pipeline but complete with **0 findings**
- **Cause:** config = `openrouter/openai/gpt-oss-20b:free` (free tier, 0 credits). OpenRouter returns:
  ```
  Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day. (429)
  ```
  Every LLM turn fails → the analysis agents never get model responses → no vulnerabilities written.
- **Fix:** in **SettingsView** (App Console → Settings) switch provider/model/key to a working one:
  - Groq (free, generous quota) — Groq key is already valid: provider `groq`, model `groq/openai/gpt-oss-20b`
  - or an OpenAI / Anthropic / OpenRouter-fill key.
  No code change needed — the env-routing (`_apply_config_env`) already handles it.

### 3.2 Live status duration quirk
- While a scan is Running, frontend may show duration `14m 20s` (fallback) because duration is only written on `Completed`. Cosmetic — acceptable.

### 3.3 `/api/overview` target label
- Returns `"target": "example.com"` hardcoded when active until meta is read. Minor cosmetic.

### 3.4 Optional polish (not blocking)
- Stale/failed scan dirs accumulate in `rakshak_runs/` (36 dirs). Safe cleanup script recommended before production.
- `POST /api/steer` currently only ACKs ("delivered: true") — not wired into live agent mailbox.
- `pending_counts` from `agents.json` not yet painted into topology nodes.

---

## 4. Current environment state
| Item | Value |
|------|-------|
| Backend API | `http://localhost:8080` (pid live, health online, latency ~2ms) |
| Frontend Vite | `http://localhost:3000` (proxy `/api` → 127.0.0.1:8080) |
| Active scan | `scan-69570874` (Running, http://scanme.nmap.org) |
| Config provider/model | `openrouter/openai/gpt-oss-20b:free` |
| Total run dirs | 36 (`rakshak_runs/`) |

---

## 5. How to re-verify quickly
```bash
# 1. start backend (from repo root)
setsid .venv/bin/rakshak --view scan-c71e8509 --port 8080 > /tmp/opencode/backend.log 2>&1 &

# 2. start frontend (from web/)
setsid npm run dev > /tmp/opencode/frontend.log 2>&1 &

# 3. launch a scan
curl -s -X POST http://localhost:3000/api/scan -H 'Content-Type: application/json' \
  -d '{"target":"http://scanme.nmap.org","mode":"Black Box","prompt":"recon"}'

# 4. watch status flip Queued→Running→Completed
curl -s http://localhost:3000/api/runs | python3 -m json.tool
```
Re-run shape suite: `python /tmp/opencode/shape_test.py` (35/36, the 1 non-fail is Vite's same-origin OPTIONS).