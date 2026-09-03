"""Unit tests for RakshakX Benchmark Protocol v2.0."""

from datetime import UTC, datetime
from pathlib import Path

from rakshak.benchmark.metrics import (
    BenchmarkPrediction,
    BenchmarkScorecard,
    BenchmarkVerdict,
    compute_f1,
    compute_precision,
    compute_recall,
    compute_verification_rate,
    evaluate_benchmark,
    evaluate_single,
)
from rakshak.benchmark.runner import freeze_environment


def test_metric_math() -> None:
    # Precision: 2 / (2 + 1) = 0.66666...
    assert abs(compute_precision(2, 1) - 2 / 3) < 1e-4
    assert compute_precision(0, 0) == 0.0

    # Recall: 2 / (2 + 1) = 0.66666...
    assert abs(compute_recall(2, 1) - 2 / 3) < 1e-4
    assert compute_recall(0, 0) == 0.0

    # F1: 2 * (0.6667 * 0.6667) / (0.6667 + 0.6667) = 0.66666...
    p = compute_precision(2, 1)
    r = compute_recall(2, 1)
    assert abs(compute_f1(p, r) - 2 / 3) < 1e-4
    assert compute_f1(0.0, 0.0) == 0.0

    # Verification Rate: 3 / 4 = 0.75
    assert compute_verification_rate(3, 4) == 0.75
    assert compute_verification_rate(0, 0) == 0.0


def test_evaluate_single() -> None:
    verdict_present = BenchmarkVerdict(
        vuln_id="VULN-01", title="SQLi", category="sqli", cwe_id="CWE-89", severity="HIGH", endpoint="/api", is_present=True
    )
    verdict_absent = BenchmarkVerdict(
        vuln_id="VULN-02", title="XSS", category="xss", cwe_id="CWE-79", severity="LOW", endpoint="/api", is_present=False
    )

    pred_verified = BenchmarkPrediction(
        vuln_id="VULN-01", title="SQLi", category="sqli", cwe_id="CWE-89", severity="HIGH", endpoint="/api", verified=True
    )
    pred_unverified = BenchmarkPrediction(
        vuln_id="VULN-01", title="SQLi", category="sqli", cwe_id="CWE-89", severity="HIGH", endpoint="/api", verified=False
    )

    res_tp = evaluate_single(pred_verified, verdict_present)
    assert res_tp.is_tp and not res_tp.is_fp and not res_tp.is_fn

    res_fn = evaluate_single(pred_unverified, verdict_present)
    assert res_fn.is_fn and not res_fn.is_tp

    res_fp = evaluate_single(pred_verified, verdict_absent)
    assert res_fp.is_fp and not res_fp.is_tp


def test_build_scorecard(tmp_path: Path) -> None:
    start = datetime.now(UTC)
    verdicts = [
        BenchmarkVerdict(vuln_id="V1", title="T1", category="c1", cwe_id="CWE-1", severity="HIGH", endpoint="/e1", is_present=True),
        BenchmarkVerdict(vuln_id="V2", title="T2", category="c2", cwe_id="CWE-2", severity="MEDIUM", endpoint="/e2", is_present=True),
    ]
    predictions = {
        "V1": BenchmarkPrediction(vuln_id="V1", title="T1", category="c1", cwe_id="CWE-1", severity="HIGH", endpoint="/e1", verified=True),
        "V2": BenchmarkPrediction(vuln_id="V2", title="T2", category="c2", cwe_id="CWE-2", severity="MEDIUM", endpoint="/e2", verified=False),
    }
    end = datetime.now(UTC)

    out_json = tmp_path / "scorecard.json"
    scorecard = evaluate_benchmark(
        scan_id="test-scan",
        target="http://test.local",
        predictions=predictions,
        verdicts=verdicts,
        assessment_start=start,
        assessment_end=end,
        output_path=out_json,
    )

    assert isinstance(scorecard, BenchmarkScorecard)
    assert scorecard.tp == 1
    assert scorecard.fn == 1
    assert scorecard.total_reference == 2
    assert scorecard.precision == 1.0  # 1 TP / (1 TP + 0 FP)
    assert scorecard.recall == 0.5     # 1 TP / (1 TP + 1 FN)
    assert out_json.exists()


def test_environment_freeze(tmp_path: Path) -> None:
    freeze = freeze_environment(
        model="opencode/big-pickle",
        provider="opencode",
        rakshak_version="2.0-community",
    )
    freeze_file = tmp_path / "freeze.json"
    h = freeze.persist(freeze_file)

    assert freeze_file.exists()
    assert len(h) == 64  # SHA-256 hex string length
    assert freeze.python.version != ""
    assert freeze.system.os_name != ""
