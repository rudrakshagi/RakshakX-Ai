#!/usr/bin/env python3
"""CLI runner for RakshakX Benchmark Protocol v2.0."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rakshak.benchmark.adapters import evaluate_live_scan, load_ground_truth, load_target_meta, vulnerabilities_to_predictions
from rakshak.benchmark.metrics import (
    BenchmarkPrediction,
    BenchmarkVerdict,
    evaluate_benchmark,
)
from rakshak.benchmark.prompts import INTEGRITY_STATEMENT, PROMPT_REGISTRY
from rakshak.benchmark.runner import freeze_environment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RakshakX Benchmark Protocol v2.0 suite & evaluation."
    )
    parser.add_argument("--scan-id", default="bench-v2-001", help="Scan ID identifier")
    parser.add_argument("--target", default="http://localhost:3000", help="Target URL / Scope")
    parser.add_argument("--target-name", default="", help="Benchmark target name: juice_shop|dvwa|metasploitable2")
    parser.add_argument("--ground-truth", type=Path, default=None, help="Path to ground-truth JSON (overrides --target-name)")
    parser.add_argument("--vulns", type=Path, default=None, help="Path to vulnerabilities.json to score (live mode)")
    parser.add_argument("--mode", default="T01", help="Benchmark prompt mode (T01..T05, A.1..A.5)")
    parser.add_argument("--model", default="opencode/big-pickle", help="LLM Model ID")
    parser.add_argument("--provider", default="opencode", help="LLM provider")
    parser.add_argument("--api-base", default="", help="LLM API base")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/benchmark_v2"),
        help="Output directory for freeze and scorecard",
    )
    parser.add_argument("--freeze-only", action="store_true", help="Capture environment freeze and exit")
    parser.add_argument("--list-prompts", action="store_true", help="List benchmark prompts and exit")
    return parser.parse_args()


def _resolve_ground_truth(args: argparse.Namespace) -> tuple[Path | None, dict]:
    if args.ground_truth and args.ground_truth.exists():
        return args.ground_truth, load_target_meta(args.ground_truth)
    name = (args.target_name or "").lower().replace("-", "_")
    mapping = {
        "juice_shop": Path("rakshak/benchmark/targets/juice_shop.json"),
        "juice-shop": Path("rakshak/benchmark/targets/juice_shop.json"),
        "dvwa": Path("rakshak/benchmark/targets/dvwa.json"),
        "metasploitable2": Path("rakshak/benchmark/targets/metasploitable2.json"),
        "metasploitable": Path("rakshak/benchmark/targets/metasploitable2.json"),
        "ms2": Path("rakshak/benchmark/targets/metasploitable2.json"),
    }
    gt = mapping.get(name)
    if gt and gt.exists():
        return gt, load_target_meta(gt)
    return None, {}


def main() -> int:
    args = parse_args()

    if args.list_prompts:
        for k, v in PROMPT_REGISTRY.items():
            print(f"\n=== {k} ===\n{v}\n")
        return 0

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print(" RakshakX Benchmark & Validation Protocol v2.0")
    print(" Company: Rudraksh AGI | Author: Aditya Kumar Mishra")
    print(f" GSTIN: 24NKPM5455A1ZX | Support: support@rudrakshai.in")
    print("==================================================")

    start_time = datetime.now(UTC)

    gt_path, target_meta = _resolve_ground_truth(args)
    prompt_verbatim = PROMPT_REGISTRY.get(args.mode) or PROMPT_REGISTRY.get(args.mode.upper()) or ""

    # 1. Environment Freeze
    print("\n[1/3] Capturing environment freeze...")
    freeze = freeze_environment(
        model=args.model,
        provider=args.provider,
        api_base=args.api_base,
        rakshak_version="2.0-community",
        target_name=target_meta.get("name", args.target_name),
        target_version=target_meta.get("version", ""),
        target_image=target_meta.get("image", ""),
        target_digest=target_meta.get("digest", ""),
        target_url=args.target,
        prompt_verbatim=prompt_verbatim,
        scope=args.target,
        started_at=start_time.isoformat(),
        ended_at=datetime.now(UTC).isoformat(),
    )
    freeze_file = output_dir / "environment_freeze.json"
    integrity_hash = freeze.persist(freeze_file)
    print(f" -> Freeze saved: {freeze_file}")
    print(f" -> Integrity Hash: {integrity_hash}")
    print(f" -> Target: {target_meta.get('name','(generic)')} {target_meta.get('version','')} image={target_meta.get('image','')}")
    print(f" -> Inference: {freeze.inference} | Hardware: {freeze.hardware.cpu_model[:50]}")
    print(f" -> Tools: {', '.join(list(freeze.security_tools.tools.keys())[:6])}")

    if args.freeze_only:
        print("\n[+] Freeze capture complete.")
        return 0

    # 2. Evaluation
    print("\n[2/3] Evaluating benchmark...")
    if args.vulns and args.vulns.exists():
        # Live mode: score real vulnerabilities.json against ground truth
        vulns = json.loads(args.vulns.read_text(encoding="utf-8"))
        if isinstance(vulns, dict):
            vulns = vulns.get("vulnerabilities", vulns.get("findings", []))
        if gt_path is None:
            print(" -> No ground-truth specified; scoring without reference is not supported.")
            print(" -> Use --target-name juice_shop|dvwa|metasploitable2 or --ground-truth <path>")
            return 1
        print(f" -> Ground truth: {gt_path} ({len(load_ground_truth(gt_path))} verdicts)")
        print(f" -> Findings: {args.vulns} ({len(vulns)} items)")
        end_time = datetime.now(UTC)
        scorecard_file = output_dir / "scorecard.json"
        scorecard = evaluate_live_scan(
            scan_id=args.scan_id,
            target=args.target,
            vulnerabilities=vulns,
            ground_truth_path=gt_path,
            assessment_start=start_time,
            assessment_end=end_time,
            output_path=scorecard_file,
        )
    else:
        # Simulation / demo mode: use ground truth if available, else stub 3
        if gt_path and gt_path.exists():
            verdicts = load_ground_truth(gt_path)
            # Simulate: half detected as verified, rest missed, plus one FP
            predictions: dict[str, BenchmarkPrediction] = {}
            for i, v in enumerate(verdicts):
                if i < len(verdicts) // 2:
                    predictions[v.vuln_id] = BenchmarkPrediction(
                        vuln_id=v.vuln_id, title=v.title, category=v.category,
                        cwe_id=v.cwe_id, severity=v.severity, endpoint=v.endpoint,
                        verified=True, match_score=0.95,
                    )
                # else: missed -> FN (no prediction)
            # add one synthetic FP
            predictions["FP-SYNTH-001"] = BenchmarkPrediction(
                vuln_id="FP-SYNTH-001", title="Synthetic false positive for demo",
                category="xss", cwe_id="CWE-79", severity="LOW", endpoint="/nonexistent",
                verified=True, match_score=0.1,
            )
            print(f" -> Demo simulation: {len(verdicts)} verdicts, {len(predictions)} predictions (half TP + 1 FP)")
            end_time = datetime.now(UTC)
            scorecard_file = output_dir / "scorecard.json"
            scorecard = evaluate_benchmark(
                scan_id=args.scan_id,
                target=args.target,
                predictions=predictions,
                verdicts=verdicts,
                assessment_start=start_time,
                assessment_end=end_time,
                output_path=scorecard_file,
            )
        else:
            # Legacy stub 3 for backwards compat when no target specified
            sample_verdicts = [
                BenchmarkVerdict(vuln_id="VULN-001", title="SQL Injection in Search Query", category="sqli", cwe_id="CWE-89", severity="HIGH", endpoint="/api/Products/search", is_present=True),
                BenchmarkVerdict(vuln_id="VULN-002", title="Reflected XSS in User Bio", category="xss", cwe_id="CWE-79", severity="MEDIUM", endpoint="/profile", is_present=True),
                BenchmarkVerdict(vuln_id="VULN-003", title="Broken Object Level Authorization (IDOR)", category="idor", cwe_id="CWE-639", severity="HIGH", endpoint="/api/Basket/1", is_present=True),
            ]
            sample_predictions = {
                "VULN-001": BenchmarkPrediction(vuln_id="VULN-001", title="SQL Injection in Search Query", category="sqli", cwe_id="CWE-89", severity="HIGH", endpoint="/api/Products/search", verified=True, match_score=1.0),
                "VULN-002": BenchmarkPrediction(vuln_id="VULN-002", title="Reflected XSS in User Bio", category="xss", cwe_id="CWE-79", severity="MEDIUM", endpoint="/profile", verified=True, match_score=1.0),
                "VULN-003": BenchmarkPrediction(vuln_id="VULN-003", title="Broken Object Level Authorization (IDOR)", category="idor", cwe_id="CWE-639", severity="HIGH", endpoint="/api/Basket/1", verified=True, match_score=1.0),
            }
            end_time = datetime.now(UTC)
            print(" -> No ground-truth target specified; using legacy 3-item stub (pass --target-name for real evaluation).")
            scorecard_file = output_dir / "scorecard.json"
            scorecard = evaluate_benchmark(
                scan_id=args.scan_id,
                target=args.target,
                predictions=sample_predictions,
                verdicts=sample_verdicts,
                assessment_start=start_time,
                assessment_end=end_time,
                output_path=scorecard_file,
            )

    # 3. Scorecard Summary
    print("\n==================================================")
    print(" RESULTS SCORECARD SUMMARY (Protocol v2.0)")
    print("==================================================")
    print(f" Target:            {scorecard.target}")
    print(f" Total Reference:   {scorecard.total_reference}")
    print(f" Total Predictions: {scorecard.total_predictions}")
    print(f" True Positives:    {scorecard.tp}")
    print(f" False Positives:   {scorecard.fp}")
    print(f" False Negatives:   {scorecard.fn}")
    print(f" True Negatives:    {scorecard.tn}")
    print(f" Precision:         {scorecard.precision:.3f}")
    print(f" Recall:            {scorecard.recall:.3f}")
    print(f" F1 Score:          {scorecard.f1:.3f}")
    print(f" Verification Rate: {scorecard.verification_rate:.3f}")
    print(f" Assessment Time:   {scorecard.assessment_time_s:.2f}s")
    print(f" Scorecard saved:   {output_dir / 'scorecard.json'}")
    print("--------------------------------------------------")
    print(f" Integrity: {INTEGRITY_STATEMENT}")
    print("==================================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
