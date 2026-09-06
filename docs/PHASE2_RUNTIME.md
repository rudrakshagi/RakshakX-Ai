# Phase 2 — Runtime Harness (container, Caido, ports, sessions)

## Problems & fixes
1. **Reaper prefix bug (asli bug):** `server.py` ka orphan-cleaner
   `rakshak-scan-*` dhoondhta tha, asli naam `rakshak-<scan_id>` hai —
   **kabhi match nahi hota tha, leak forever.** Ab sahi prefix +
   `_is_scan_container_name()` helper jo `rakshakx-juice-shop`/`dvwa` ko
   kabhi nahi chhuta (defense-in-depth: docker substring filter bhi match
   nahi karta, empirically verified).
2. **Stale takeover:** `create_or_reuse` same-naam ka purana container pehle
   hatata hai (naya `remove_container_by_name()`), phir fresh banata hai.
3. **Port collision:** `_find_free_port` ka TOCTOU race — `create_sandbox` ab
   port-conflict pe 3 baar fresh ports ke saath retry karta hai.
4. **Caido retry:** readiness polling to tha, par login/project/connect
   single-shot tha — ek 502 = poore scan me no-proxy. Ab 3 attempts
   exponential backoff (`_connect_sdk` extracted).
5. **Bonus:** `SandboxSession.exec/write/read` async the par andar
   sync-blocking — ab `to_thread` me (Phase-1 jaisa bug).

## Proof
- `tests/test_runtime_harness.py` — 20/20 (retry counts exact, sticky order,
  caido fail-once→success, to_thread responsiveness).
- E2E real Docker — 11/11: stale plant → takeover (nayi id), exec/write/read
  sahi, real Caido bootstrap 11s me client, targets untouched, zero leftovers.

## Final-e2e addendum (Juice Shop verification scans)
`scan-b1463aa9` (pre-fix) me live bug mila: `caido_api.py` ne nonexistent
`client.execute_graphql()` call kiya — installed SDK me sirf
`client.graphql.query` hai, isliye **har proxy query tool live fail** ho raha
tha. Fix: `_execute_graphql()` helper (modern path + legacy fallback) +
query ko installed schema se align kiya (`HTTPQLInput`, `RequestResponseOrderInput`,
real node fields — pehla attempt `Unknown type "RequestFilter"` pe fail hua tha).
- `tests/test_caido_api.py` — 9/9; live traffic e2e 6/6 (4 real items returned).
- `scan-d57df93e` (post-fix, 12 turns): **zero tool errors**, heartbeat fresh,
  PDF/SARIF/freeze sab bane, clean Completed. 0 findings = 12-turn budget me
  small model ne kuch confirm nahi kiya (60-turn run me same pipeline pe 3 mile
  the) — harness bug nahi.
