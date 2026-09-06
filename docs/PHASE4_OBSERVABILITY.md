# Phase 4 — Observability Harness (logs, reaper, supervisor)

## Problems & fixes
1. **Sidecar supervisor** (`rakshak/interface/viewer/supervisor.py`, NEW):
   backend me daemon thread (30s tick) jo `:8787` + `:3000` probe karta hai;
   down mile to canonical logs me single-service restart.
   Kill-switch: `RAKSHAK_SUPERVISE_SIDECARS=0`. Live kill-test proven.
2. **Trio-trap (live pakda):** web ka `npm run dev` concurrently TRIO hai —
   supervisor usse restart karta to duplicate backends `:8080` pe ladte (ek
   ghost backend ne apna supervisor chala ke double-restart bhi kar diya).
   Ab single-service commands: `node server.js` + absolute vite binary.
3. **Confirm-down double probe:** ek flake pe duplicate spawn → `EADDRINUSE`
   crash. Ab 3s gap pe do probe + 60s cooldown.
4. **Backend log rotation:** `logs/backend.log` 2MB×3, idempotent;
   restart-sprawl (`*-relaunch*.log`) band — sab canonical files me.
5. **Scan-scoped logs:** `/api/logs?scan=<id>` substring filter + echo.
6. **agents.json terminal marking:** crash/completion pe disk truth bhi
   terminal (offline scripts ke liye; UI pehle se normalize karta tha).

## Proof
- `tests/test_observability_harness.py` — 11/11 (rollover, cooldown,
  kill-switch, terminal marking, corrupt-JSON no-raise).
- Live: asli bridge PID kill → 000 → 45s me 200, exactly 1 instance.
- `?scan=scan-` live verified (echo + all-match).
