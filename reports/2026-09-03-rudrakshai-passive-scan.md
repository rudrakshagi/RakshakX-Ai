# Passive Security Assessment — rudrakshai.in (2026-09-03)

- **Scan ID**: `rudra-passive` · **Mode**: quick · **Scope**: `https://rudrakshai.in`
- **Authorization**: site owned by Rudraksh AGI / Aditya Kumar Mishra (matches README proprietor); passive recon only, no exploitation, no state-changing requests.
- **Full step-by-step logs**: `logs/rudra-passive/` (`00_prompt.md`, `01_transcript.md`, `02_files_written.md`, `03_issues_and_caveats.md`, `raw_scan.log`).

## Method
Agent workflow (`run_rakshak_scan`, opencode-free model, Docker sandbox): DNS (`dig`), TLS (`openssl s_client`), headers (`curl -sI`), HTML fingerprint (`curl -s`). 17 successful tool turns, 1 finding filed via `create_vulnerability_report`.

## Verified results (direct non-proxied re-check, 2026-09-03)

```
HTTP/2 200 · server: Netlify
strict-transport-security: max-age=31536000   → PRESENT
```

| Header | Agent claim | Direct verification |
|---|---|---|
| HSTS | missing | **PRESENT** — agent finding was wrong here (proxy artifact) |
| X-Frame-Options | missing | **Missing — CONFIRMED** |
| X-Content-Type-Options | missing | **Missing — CONFIRMED** |
| Content-Security-Policy | missing | **Missing — CONFIRMED** |
| X-XSS-Protection | missing | Missing (deprecated header, low value) |

Server fingerprint correction: site is hosted on **Netlify** (static), not a "Caido-based application" — the agent saw the sandbox proxy's page.

## Corrected finding
- **Missing security headers (X-Frame-Options, X-Content-Type-Options, CSP)** — CWE-16, hardening-level. No exploitable vulnerability (SQLi/XSS/RCE) was tested or found; coverage was passive-only and the run never reached `finish_scan`.
- **Remediation**: add `X-Frame-Options: DENY` (or `SAMEORIGIN`), `X-Content-Type-Options: nosniff`, and a baseline `Content-Security-Policy` at the Netlify edge (`netlify.toml` headers or `_headers` file). HSTS already OK.

## Run limitations (honest)
- `finish_scan` never called — agent looped on an `exec_command {"shell": true}` schema error until timeout; report narrative sections are placeholders.
- All in-sandbox evidence passed through the Caido MITM proxy; only the table above is direct-verified.
- Fixed after this run: shell-contract hardening in `rakshak/agents/factory.py` (`_configure_shell_tools`) + regression tests `tests/test_agents_shell_contract.py`.
