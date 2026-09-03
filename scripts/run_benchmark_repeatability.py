#!/usr/bin/env python3
"""Repeatability Protocol: run same frozen config 10 times, aggregate metrics."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from rakshak.benchmark.adapters import evaluate_live_scan, load_ground_truth
from rakshak.benchmark.metrics import BenchmarkPrediction, evaluate_benchmark
from rakshak.benchmark.prompts import INTEGRITY_STATEMENT, T01_PROMPT
from rakshak.benchmark.runner import freeze_environment


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RakshakX Benchmark Repeatability Protocol (10 runs, Protocol v2.0)")
    p.add_argument("--target", default="http://localhost:3001", help="Target URL / IP")
    p.add_argument("--target-name", default="juice_shop", help="juice_shop|dvwa|metasploitable2")
    p.add_argument("--ground-truth", type=Path, default=None, help="Override ground-truth JSON path")
    p.add_argument("--model", default="opencode/big-pickle")
    p.add_argument("--provider", default="opencode")
    p.add_argument("--api-base", default="")
    p.add_argument("--runs", type=int, default=10, help="Number of repetitions (default 10)")
    p.add_argument("--output-dir", type=Path, default=Path("reports/benchmark_v2/repeatability"))
    p.add_argument("--simulate", action="store_true", help="Simulate without live scans (deterministic demo)")
    p.add_argument("--vulns-dir", type=Path, default=None, help="Directory containing per-run vulnerabilities.json files for offline aggregation")
    return p.parse_args()


def _resolve_gt(args) -> Path | None:
    if args.ground_truth and args.ground_truth.exists():
        return args.ground_truth
    mapping = {
        "juice_shop": Path("rakshak/benchmark/targets/juice_shop.json"),
        "juice-shop": Path("rakshak/benchmark/targets/juice_shop.json"),
        "dvwa": Path("rakshak/benchmark/targets/dvwa.json"),
        "metasploitable2": Path("rakshak/benchmark/targets/metasploitable2.json"),
    }
    return mapping.get((args.target_name or "").lower())


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print(" RakshakX Repeatability Protocol — 10 Runs")
    print(" Benchmark v2.0 | T01 prompt frozen")
    print("==================================================")
    print(f" Target: {args.target} ({args.target_name})")
    print(f" Runs:   {args.runs} | Mode: {'SIMULATE' if args.simulate else 'LIVE' if not args.vulns_dir else 'OFFLINE'}")
    print(f" Output: {args.output_dir}")

    gt_path = _resolve_gt(args)
    if gt_path is None or not gt_path.exists():
        print(f"ERROR: Ground truth not found for target-name={args.target_name}. Use --ground-truth <path>")
        return 1

    verdicts = load_ground_truth(gt_path)
    print(f" Ground truth: {gt_path} ({len(verdicts)} verdicts)")

    # Environment freeze (once, reused)
    freeze = freeze_environment(
        model=args.model,
        provider=args.provider,
        api_base=args.api_base,
        rakshak_version="2.0-community",
        target_name=args.target_name,
        target_url=args.target,
        prompt_verbatim=T01_PROMPT,
        scope=args.target,
        started_at=datetime.now(UTC).isoformat(),
    )
    freeze.persist(args.output_dir / "environment_freeze.json")
    print(f" Freeze hash: {freeze.compute_integrity_hash()[:16]}...")

    # Collect per-run scorecards
    per_run: list[dict] = []

    if args.vulns_dir and args.vulns_dir.exists():
        # Offline aggregation: score existing vulns files
        vuln_files = sorted(args.vulns_dir.glob("*/vulnerabilities.json")) + sorted(args.vulns_dir.glob("vulnerabilities_*.json"))
        if not vuln_files:
            vuln_files = sorted(args.vulns_dir.glob("*.json"))
        for i, vf in enumerate(vuln_files[: args.runs]):
            try:
                vulns = json.loads(vf.read_text(encoding="utf-8"))
                if isinstance(vulns, dict):
                    vulns = vulns.get("vulnerabilities", [])
                sc = evaluate_live_scan(
                    scan_id=f"repeat-{i+1:02d}",
                    target=args.target,
                    vulnerabilities=vulns,
                    ground_truth_path=gt_path,
                    assessment_start=datetime.now(UTC),
                    assessment_end=datetime.now(UTC),
                )
                per_run.append({
                    "run": i + 1, "scan_id": sc.scan_id, "target": sc.target,
                    "tp": sc.tp, "fp": sc.fp, "fn": sc.fn, "tn": sc.tn,
                    "precision": sc.precision, "recall": sc.recall, "f1": sc.f1,
                    "verification_rate": sc.verification_rate,
                    "assessment_time_s": sc.assessment_time_s,
                    "candidate_findings": sc.total_predictions,
                    "confirmed_findings": sc.tp,
                    "report_generated": True,
                    "source": str(vf),
                })
            except Exception as e:
                print(f" [!] Failed to score {vf}: {e}")
    elif args.simulate:
        # Deterministic simulation with slight variance
        import random
        random.seed(42)
        for run_idx in range(1, args.runs + 1):
            start = datetime.now(UTC)
            # Simulate: 50-70% detection + 0-2 FP jitter
            detect_ratio = 0.5 + random.random() * 0.2
            num_detect = max(1, int(len(verdicts) * detect_ratio))
            num_fp = random.randint(0, 2)
            predictions: dict[str, BenchmarkPrediction] = {}
            for j in range(num_detect):
                v = verdicts[j]
                predictions[v.vuln_id] = BenchmarkPrediction(
                    vuln_id=v.vuln_id, title=v.title, category=v.category,
                    cwe_id=v.cwe_id, severity=v.severity, endpoint=v.endpoint,
                    verified=random.random() > 0.15, match_score=0.9,
                )
            for k in range(num_fp):
                predictions[f"FP-SIM-{run_idx}-{k}"] = BenchmarkPrediction(
                    vuln_id=f"FP-SIM-{run_idx}-{k}", title="Simulated FP",
                    category="xss", cwe_id="CWE-79", severity="LOW", endpoint="/fp",
                    verified=True, match_score=0.2,
                )
            time.sleep(0.02)
            end = datetime.now(UTC)
            sc = evaluate_benchmark(
                scan_id=f"repeat-sim-{run_idx:02d}",
                target=args.target,
                predictions=predictions,
                verdicts=verdicts,
                assessment_start=start,
                assessment_end=end,
            )
            duration = (end - start).total_seconds()
            # Persist per-run scorecard
            run_dir = args.output_dir / f"run_{run_idx:02d}"
            run_dir.mkdir(parents=True, exist_ok=True)
            sc.persist(run_dir / "scorecard.json")
            per_run.append({
                "run": run_idx, "scan_id": sc.scan_id, "target": sc.target,
                "tp": sc.tp, "fp": sc.fp, "fn": sc.fn, "tn": sc.tn,
                "precision": sc.precision, "recall": sc.recall, "f1": sc.f1,
                "verification_rate": sc.verification_rate,
                "assessment_time_s": duration,
                "candidate_findings": sc.total_predictions,
                "confirmed_findings": sc.tp,
                "report_generated": True,
            })
            print(f" Run {run_idx:02d}: TP={sc.tp} FP={sc.fp} FN={sc.fn} P={sc.precision:.3f} R={sc.recall:.3f} F1={sc.f1:.3f} T={duration:.2f}s")
    else:
        print("\n[!] Live repeatability requires a running target and LLM. Use --simulate for demo or --vulns-dir for offline aggregation.")
        print("    Example: python scripts/run_benchmark_repeatability.py --simulate --runs 10")
        return 1

    if not per_run:
        print("No runs collected.")
        return 1

    # Aggregate stats
    def _stats(key: str) -> dict:
        vals = [r[key] for r in per_run]
        return {
            "mean": round(statistics.mean(vals), 4) if vals else 0,
            "stdev": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0,
            "min": round(min(vals), 4) if vals else 0,
            "max": round(max(vals), 4) if vals else 0,
        }

    summary = {
        "protocol_version": "2.0",
        "target": args.target,
        "target_name": args.target_name,
        "ground_truth": str(gt_path),
        "total_verdicts": len(verdicts),
        "runs": len(per_run),
        "prompt": T01_PROMPT,
        "integrity_statement": INTEGRITY_STATEMENT,
        "generated_at": datetime.now(UTC).isoformat(),
        "per_run": per_run,
        "aggregate": {
            "precision": _stats("precision"),
            "recall": _stats("recall"),
            "f1": _stats("f1"),
            "verification_rate": _stats("verification_rate"),
            "assessment_time_s": _stats("assessment_time_s"),
            "tp": _stats("tp"),
            "fp": _stats("fp"),
            "fn": _stats("fn"),
            "candidate_findings": _stats("candidate_findings"),
            "confirmed_findings": _stats("confirmed_findings"),
        },
    }

    summary_path = args.output_dir / "repeatability_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[+] Summary written: {summary_path}")

    # Also emit summary.md table
    md_lines = [
        "# RakshakX Repeatability Summary (Protocol v2.0)",
        f"\n**Target**: `{args.target}` ({args.target_name}) | **Runs**: {len(per_run)} | **Prompt**: T01",
        f"**Ground Truth**: `{gt_path}` ({len(verdicts)} verdicts) | **Generated**: {summary['generated_at']}",
        "\n| Run | Candidates | Confirmed (TP) | FP | FN | Precision | Recall | F1 | VR | Time(s) |",
        "|----:|----------:|---------------:|---:|---:|----------:|-------:|----:|---:|--------:|",
    ]
    for r in per_run:
        md_lines.append(f"| {r['run']:02d} | {r['candidate_findings']} | {r['confirmed_findings']} | {r['fp']} | {r['fn']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | {r['verification_rate']:.3f} | {r['assessment_time_s']:.2f} |")
    md_lines.append(f"\n**Aggregate (mean ± stdev)**: P={summary['aggregate']['precision']['mean']:.3f}±{summary['aggregate']['precision']['stdev']:.3f}, "
                    f"R={summary['aggregate']['recall']['mean']:.3f}±{summary['aggregate']['recall']['stdev']:.3f}, "
                    f"F1={summary['aggregate']['f1']['mean']:.3f}±{summary['aggregate']['f1']['stdev']:.3f}")
    md_lines.append(f"\n*Integrity Statement*: {INTEGRITY_STATEMENT}")
    md_path = args.output_dir / "repeatability_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[+] Markdown summary: {md_path}")

    print("\n==================================================")
    print(f" Completed {len(per_run)} runs. Mean F1={summary['aggregate']['f1']['mean']:.3f} mean P={summary['aggregate']['precision']['mean']:.3f} mean R={summary['aggregate']['recall']['mean']:.3f}")
    print("==================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
