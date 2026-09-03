# Daily Work Report — 2026-09-03 (RakshakX-Ai)

## 1. AI agent loop + opencode-free provider (morning)
- **Problem**: live E2E needed a real AI API; opencode free gateway (`https://opencode.ai/zen/v1`, no-auth) rejected requests.
- **Fix** (`rakshak/config/models.py`, `rakshak/core/runner.py`): opencode-free detection (`oc/` prefix or `provider: opencode-free`), model alias normalization, required headers (`x-opencode-client: desktop`, empty `Authorization`), dummy key for litellm.
- **Verified**: real tool-calling loop (`add(100,5) → 105`), live E2E `test_live_target.py --run-live` **passed in 73.92s** against Juice Shop; agent performed genuine recon reasoning + curl probing.
- **Docs**: README "Option A2: OpenCode Free"; `LLMSettings.provider` field + config loading.

## 2. Attack-tool execution path (confirmed)
- Agent `exec_command` → SDK `Shell()` capability → `SDKSandboxSession` → `docker_client.exec_command` → `container.exec_run` as `pentester` on bridge network. Shell tools are Docker-backed; proxy/bookkeeping tools are in-process.

## 3. Tool-schema naturalness (test + fix)
- **Found**: zero per-parameter descriptions; optional/defaulted params wrongly `required` (SDK marks everything required).
- **Fix**: `Annotated[..., "..."]` descriptions on every param across 8 tool modules; `factory._normalize_tool_schema` recomputes `required` (default/nullable → optional). E.g. `list_requests` req=None, `create_agent` req=[name,task].
- **Tests**: `tests/test_tool_schemas.py` (6 tests: validity, descriptions, required-correctness, round-trip, validation errors). Live-AI check: model correctly chained `load_skill → create_todo → list_todos`.
- **Suite**: 128 unit passed; ruff + mypy clean.

## 4. Deterministic agent-loop E2E
- `tests/e2e/test_scan_agent_loop.py`: scripted fake `Model` + real `Runner` + real tools (2 tests: tool execution persists state; CVSS rejection flows back into loop). 11/11 e2e pass with mocked + viewer suites.

## 5. Frontend ↔ backend verification
- Backend live: `/api/system/health`, `/api/runs`, `/api/overview` → 200. Vite `/api → 127.0.0.1:8080` proxy matches; `ScanCreator` payload shape matches `/api/scan` handler.
- **Gap found**: backend ignores `modules`/`targetType` — UI toggles don't constrain the agent; only free-text `prompt` reaches the runner.

## 6. rudrakshai.in passive scan (user-owned; Rudraksh AGI / Aditya Kumar Mishra)
- Ran `rudra-passive` (quick, passive-only prompt, budget $2, 20 turns). Ownership verified (README ↔ site).
- Agent did real recon (DNS/TLS/headers, 17 turns) and filed 1 finding (missing security headers, CWE-16, CVSS 0.0/none).
- **Direct re-verification corrected it**: HSTS is PRESENT (`max-age=31536000`); X-Frame-Options / X-Content-Type-Options / CSP confirmed missing; host is Netlify, not Caido-app. Full detail: `reports/2026-09-03-rudrakshai-passive-scan.md`, steps: `logs/rudra-passive/`.
- **Failure**: `finish_scan` never called — model looped on `exec_command {"shell": true}` (bool vs string schema) until timeout kill.
- **Fix applied**: `_configure_shell_tools` in `rakshak/agents/factory.py` (contract description + bool-shell coercion) wired via `Shell(configure_tools=...)`; regression suite `tests/test_agents_shell_contract.py` (6 tests, all pass).

## Test status at end of day
- New: 6 schema + 2 loop-E2E + 6 shell-contract tests — all pass.
- Full unit: 128 passed (pre-fix baseline); factory subset re-verified post-fix (11 passed); ruff + mypy clean on touched files.
