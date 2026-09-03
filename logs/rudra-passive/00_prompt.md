# Log 00 — Prompt (exact input given to the agent workflow)

## Run parameters (`logs/rudra-passive/driver_script.py`)

| Param | Value |
|---|---|
| `target` | `https://rudrakshai.in` |
| `scan_id` | `rudra-passive` |
| `scan_mode` | `quick` |
| `scope` | `https://rudrakshai.in` |
| `max_budget_usd` | `2.0` |
| `max_turns` | `20` |
| Model | `openai/oc/nemotron-3.5-lightning-free` via `https://opencode.ai/zen/v1` (RakshakProvider, opencode-free mode) |
| Sandbox | RakshakX Docker sandbox (`SDKSandboxSession` → `docker_client.exec_command`, user `pentester`, bridge network, Caido proxy on `127.0.0.1:48080`) |

## Exact `prompt_verbatim` sent (also stored in `run_meta.json`)

```text
PASSIVE RECONNAISSANCE ONLY on https://rudrakshai.in.
This site is owned by the user requesting the scan (Rudraksh AGI / Aditya Kumar Mishra).

Allowed (read-only, non-intrusive):
- DNS enumeration (dig, nslookup, host)
- TLS certificate inspection (openssl s_client, curl -vI)
- HTTP security headers review (curl -sI / -s)
- Technology fingerprinting from response headers and HTML meta tags

STRICTLY FORBIDDEN:
- brute-force, fuzzing, exploitation, PoC execution
- sqlmap, nuclei intrusive scans, login attempts
- any state-changing request (POST/PUT/DELETE)
- scanning any host other than rudrakshai.in

File vulnerability reports ONLY for confirmed passive observations
(e.g. missing security headers). End by calling finish_scan with a full report.
```

## What the runner prepended (message [0] in DB)

```text
Target: https://rudrakshai.in
Scope: https://rudrakshai.in
Benchmark Mode: quick

<PROMPT ABOVE>
```

## Ownership basis

- `README.md:10` — "Designed & Architected by Parent Company: Rudraksh AGI (rudrakshai.in) · Proprietor: Aditya Kumar Mishra"
- `https://rudrakshai.in/` homepage (HTTP 200, fetched once for verification) — title "Rudraksh AGI | AI-Native Software Company", body lists "Aditya Kumar Mishra (Proprietor)".
- Scope guard (`rakshak/core/runner.py::_is_allowed_scope`) returned `False` for the public hostname as designed, logged `Scope guard: target ... not in lab allowlist`, and continued in warn-only mode (hard block is commented out).
