# Phase 5 — Report + Benchmark Harness (severity, scorecard, freeze)

## Problems & fixes
1. **Central severity normalizer** (`rakshak/report/severity.py`, NEW):
   5 jagah alag-alag `.lower()`/exact-match tha — "Critical"/"NONE"/""
   counts se gir jaate the. Ab `normalize_severity()` har jagah
   (creation funnel, SARIF, PDF, adapters, viewer counts + naya
   `informational` key). CVSS 0.0 → `"none"` → `"informational"`.
2. **Scorecard edges** (`metrics.py`): `verified="false"` string ab TP nahi
   banata (truthiness bug); duplicate GT ids dedupe (first wins + warning,
   total_reference=unique); negative duration clamp; empty-vs-empty = zeros.
3. **Freeze verification** (`runner.verify_environment_freeze` + repeatability
   gate): TAMPERED → abort. `--vulns-dir` fallback `environment_freeze.json`
   ko score karke TP=0/FN=12 dikha raha tha (E2E ne pakda) — ab known
   artifacts skip, real `vulnerabilities.json` score hota hai.

## Proof
- `tests/test_report_benchmark_harness.py` — 49/49 (0.0-vector → none →
  informational verified real `cvss` lib se).
- E2E: simulate 3 runs exit 0 (mean P=0.917 R=0.444 F1=0.592), freeze
  VERIFIED printed, tamper → mismatch detected, offline real Juice data
  TP=1 FP=2 FN=11.
