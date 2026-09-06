# Phase 3 — Tool Harness (spillway + model-friendly errors)

## Problems & fixes
1. **Spillway unwired:** `bound_and_store` bana tha par use koi karta hi nahi
   tha. Ab `sdk_session._exec_internal` bada output usi se bhejta hai —
   model ko **head+tail window** (exit codes/error footers tail me hote hain),
   FULL text sandbox spill file me (`/workspace/.rakshak/spill/out_*.txt`).
   Exec budget purana 4k threshold preserve karta hai
   (100 lines / 4KB / 1500 tokens).
2. **Per-scan writer isolation:** global spill-writer se concurrent scans ka
   output galat sandbox me ja sakta tha — ab ContextVar ambient writer +
   global fallback.
3. **17/17 tools pe hooks:** unhandled crash/timeout pe raw traceback ki jagah
   `{"success": False, "error": <one-line>, "hint": <actionable>}` —
   naya `rakshak/tools/errors.py` (`failure_error_function` /
   `timeout_error_function`, SDK 0.20). Timeout hint: NARROWER chalao,
   repeat mat karo.

## Proof
- `tests/test_tool_harness.py` — 22/22 (17 hooks discovered, not hardcoded —
  naya tool bhool gaya to test pakdega; ambient-beats-global; head+tail keeps
  `line 0` + `line 999`).
- E2E real Docker — 18/18: `seq 1 2000` → model ko 2437 bytes, spill me poore
  2000 lines; 81KB blob → 36KB model + full spill; `echo` byte-exact.
- 1 source fix test ne karwaya: exec budget default 100KB model context me
  bloat karta — 4k cap rakha.
