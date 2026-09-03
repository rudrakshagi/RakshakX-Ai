# Log 02 — Files written (kaunsi file, kisne, kya likha)

Run dir: `rakshak_runs/rudra-passive/` — copies of key files are in this log folder.
Raw stdout/stderr: `raw_scan.log` (350 lines).

## Files written by the RUNNER (scaffolding, before/around the agent)

| File | Written by | Kya likha |
|---|---|---|
| `run_meta.json` | `run_rakshak_scan` | scan_id `rudra-passive`, target/scope `https://rudrakshai.in`, mode `quick`, full `prompt_verbatim` (copy: `run_meta.json`) |
| `environment_freeze.json` | benchmark runner `freeze_environment` | Python/OS/hardware/Docker/LLM/tool snapshot at scan start |
| `.state/agents.db` | SDK session layer | 1 session (`7b339f4f`), 52 messages: task input + 17 reasoning + 17 tool calls + 17 tool outputs |
| `.state/agents.json` | coordinator | `{"7b339f4f": "Root Orchestrator"}`, status `running` (process killed before graceful finish, so status never flipped to completed) |

## Files written by the AGENT (via tools)

| File (via tool) | Tool call | Kya likha |
|---|---|---|
| `vulnerabilities.json` entry `d951a2c9d606ec3d` | `create_vulnerability_report` (step [50]) | "Missing Security Headers on rudrakshai.in", CWE-16, CVSS `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N` (0.0/none), endpoint `https://rudrakshai.in/`, PoC `curl -sI https://rudrakshai.in/` (copy: `vulnerabilities.json`) |
| `think` scratchpad | `think` (step [47]) | Private recon summary (DNS nsone.net NS, LE cert EC-P256, header observations) — recorded, returned `thought_recorded` |

## Files written by the REPORT pipeline (post-agent, auto-generated)

| File | Kya likha |
|---|---|
| `report.md` | 12-section assessment report, 1 confirmed finding (copy: `final_report.md`) |
| `report.pdf` | Same report rendered to PDF |
| `sarif.json` | SARIF version of the 1 finding |

## Files in THIS log folder

| File | Source |
|---|---|
| `00_prompt.md` | Exact prompt + run params (this run's documentation) |
| `01_transcript.md` | Auto-generated from `agents.db` — all 52 messages step-by-step |
| `02_files_written.md` | This file |
| `03_issues_and_caveats.md` | What failed / what to not trust blindly |
| `final_report.md` | Copy of `rakshak_runs/rudra-passive/report.md` |
| `vulnerabilities.json` | Copy of the finding |
| `run_meta.json` | Copy of run metadata |
| `driver_script.py` | Copy of `/tmp/opencode/rudra_scan.py` used to launch |
| `raw_scan.log` | Copy of full stdout/stderr (`/tmp/opencode/rudra_scan.log`) |

## What was NEVER written (did not happen)

- `finish_scan` was **never called** — no executive summary/methodology/technical-analysis/recommendations narrative sections were populated (report §1/§6 show placeholder text).
- No child agents were spawned (`create_agent` never called) — single Root Orchestrator only.
- No `notes/todos` were used. No Caido proxy data (client failed to bootstrap: "Could not bootstrap Caido client; proceeding with direct scanning").
