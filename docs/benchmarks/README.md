# RakshakX Benchmarks — Research / Benchmarks

Detailed benchmark reports are published here and served via the product console at `Research / Benchmarks` (`/api/benchmark/*`).

- Protocol: `docs/BENCHMARK_V2_PROTOCOL.md` (Version 2.0)
- Latest freeze: `reports/benchmark_v2/environment_freeze.json` (SHA-256 integrity hash in file)
- Latest scorecard: `reports/benchmark_v2/scorecard.json`
- Repeatability (10 runs, T01 frozen): `reports/benchmark_v2/repeatability/repeatability_summary.json` + `.md`
- Target fixtures: `rakshak/benchmark/targets/{juice_shop,dvwa,metasploitable2}.json` (pinned digests: juice-shop `73c53fbf...` / Id `0cec496d...`, dvwa `dae203fe...` / Id `ab0d8358...`, sandbox `cd1370fa...`)
- Harness: `containers/docker-compose.benchmark.yml` (`bkimminich/juice-shop:latest` :3001, `vulnerables/web-dvwa:latest` :3002, Metasploitable2 OVA)
- Runners: `scripts/run_benchmark_v2.py` and `scripts/run_benchmark_repeatability.py`
- Freeze: hardware `AMD Ryzen 5 8645HS`, 12 tools captured via sandbox `rakshakx/sandbox:latest` (nmap 7.99, nuclei 3.11.0, semgrep 1.173.0, httpx 1.10.0, etc.), sandbox digest `cd1370fa0e14...`

## Integrity Statement

The benchmark measures RakshakX on selected controlled environments and does not establish universal vulnerability detection, zero-day detection, enterprise-scale performance, or security of arbitrary real-world systems.

## Company Summary (for Rudraksh AGI site)

> RakshakX Community Edition was evaluated under Benchmark & Validation Protocol v2.0 against self-hosted lab targets (primary: OWASP Juice Shop 17.2.1). Measurements include Precision, Recall, F1, Verification Rate, and Assessment Time with full environment freeze and integrity hash. See full report at `/research/benchmarks` on the product site.

Do not publish a generic accuracy percentage unless the classification task and denominator are rigorously defined.

## Reproduce

```bash
docker compose -f containers/docker-compose.benchmark.yml up -d
python scripts/run_benchmark_v2.py --target-name juice_shop --target http://localhost:3001
python scripts/run_benchmark_repeatability.py --simulate --runs 10 --target-name juice_shop
```
