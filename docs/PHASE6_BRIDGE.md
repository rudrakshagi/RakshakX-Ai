# Phase 6 — Bridge Harness (approval + model fallback)

## Problems & fixes (`opencode-bridge/`)
1. **Approval single home** (`lib/approval.js`, NEW): gating check `chat.js`
   me inline tha, test haath se replica karta tha (drift-prone). Ab
   `resolveApproval()` — unknown mode → auto+warn; manual+safe → execute;
   deny → **sticky** (same name+args, naya call_id bhi auto-deny, dobara
   prompt nahi); approve clears sticky.
2. **Model fallback** (`opencodeConnector.js`): `chatWithFallback()` — 429 /
   5xx / network / model-blaming-400 pe **ek retry** fallback model pe
   (`RAKSHAK_FALLBACK_MODEL`, default `oc/big-pickle`). 400-args-error aur
   401/403 pe NO fallback (dobara fail hoga / same credentials).
   Agentic loop fallback pe stick rehta hai (per-turn flap nahi).
3. **Wiring** (`routes/chat.js`): loop + plain path dono fallback pe;
   unknown approval.mode ek baar warn + auto.

## Proof
- `scripts/test-approval-gating.js` (rewritten, real helper) — 23/23.
- `scripts/test-fallback.js` (new) — 37/37 (already-on-fallback → throws,
  no infinite loop).
- Regressions: agentic-loop 16, chat + frontend-chat live PASS.
- Live: unknown `approval.mode` → 200 (fail-open proven).
