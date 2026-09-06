"""RakshakX Benchmark Protocol v2.0 -- evaluation metrics and scoring."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2.0"


@dataclass
class BenchmarkVerdict:
    """Ground-truth verdict for a single vulnerability reference item."""

    vuln_id: str
    title: str
    category: str
    cwe_id: str
    severity: str
    endpoint: str
    is_present: bool = True


@dataclass
class BenchmarkPrediction:
    """Agent-generated prediction matched against a reference verdict."""

    vuln_id: str
    title: str
    category: str
    cwe_id: str
    severity: str
    endpoint: str
    verified: bool = False
    match_score: float = 0.0
    assessed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        # Callers pass verified as "true"/"false"/1/0 from JSON — a raw
        # string "false" is truthy in Python and would score a miss as TP.
        self.verified = coerce_verified(self.verified)


def coerce_verified(value: object) -> bool:
    """Normalize truthy JSON-ish values to a real bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "verified", "confirmed", "yes", "1")
    return bool(value)


@dataclass
class EvaluationResult:
    """Raw per-item evaluation result."""

    vuln_id: str
    prediction: BenchmarkPrediction | None
    verdict: BenchmarkVerdict
    is_tp: bool = False
    is_fp: bool = False
    is_fn: bool = False
    is_tn: bool = False


@dataclass
class BenchmarkScorecard:
    """Aggregate Benchmark Protocol v2.0 scorecard."""

    protocol_version: str = PROTOCOL_VERSION
    scan_id: str = ""
    target: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    total_reference: int = 0
    total_predictions: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    verification_rate: float = 0.0
    assessment_time_s: float = 0.0
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def persist(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        logger.info("Benchmark scorecard written to %s", output_path)


def _safe_div(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def compute_precision(tp: int, fp: int) -> float:
    """Precision = TP / (TP + FP)."""
    return _safe_div(tp, tp + fp)


def compute_recall(tp: int, fn: int) -> float:
    """Recall = TP / (TP + FN)."""
    return _safe_div(tp, tp + fn)


def compute_f1(precision: float, recall: float) -> float:
    """F1 = 2 * (Precision * Recall) / (Precision + Recall)."""
    denominator = precision + recall
    return (2.0 * precision * recall) / denominator if denominator else 0.0


def compute_verification_rate(verified: int, total_predictions: int) -> float:
    """Verification Rate = Verified Predictions / Total Predictions."""
    return _safe_div(verified, total_predictions)


def evaluate_single(
    prediction: BenchmarkPrediction | None,
    verdict: BenchmarkVerdict,
) -> EvaluationResult:
    """Evaluate a single prediction against its ground-truth verdict."""
    result = EvaluationResult(
        vuln_id=verdict.vuln_id,
        prediction=prediction,
        verdict=verdict,
    )

    if prediction is None:
        if verdict.is_present:
            result.is_fn = True
        else:
            result.is_tn = True
        return result

    verified = coerce_verified(prediction.verified)
    if verdict.is_present and verified:
        result.is_tp = True
    elif verdict.is_present and not verified:
        result.is_fn = True
    elif not verdict.is_present and verified:
        result.is_fp = True
    else:
        result.is_tn = True

    return result


def build_scorecard(
    *,
    scan_id: str,
    target: str,
    predictions: dict[str, BenchmarkPrediction],
    verdicts: list[BenchmarkVerdict],
    assessment_start: datetime,
    assessment_end: datetime,
) -> BenchmarkScorecard:
    """Build a full Benchmark Protocol v2.0 scorecard from predictions and ground-truth verdicts."""
    # Dedupe verdicts by id (first wins): duplicate ground-truth entries
    # would otherwise inflate total_reference while verdict_map collapses
    # them, skewing recall denominators.
    verdict_map: dict[str, BenchmarkVerdict] = {}
    for v in verdicts:
        if v.vuln_id in verdict_map:
            logger.warning("Duplicate ground-truth vuln_id %s ignored (first wins).", v.vuln_id)
            continue
        verdict_map[v.vuln_id] = v
    unique_verdicts = list(verdict_map.values())
    all_ids = sorted(set(verdict_map) | set(predictions))

    results: list[EvaluationResult] = []
    tp = fp = fn = tn = verified_count = 0

    for vid in all_ids:
        pred = predictions.get(vid)
        verdict = verdict_map.get(vid)
        if verdict is None:
            if pred is not None:
                fp += 1
                results.append(
                    EvaluationResult(vuln_id=vid, prediction=pred, verdict=BenchmarkVerdict(
                        vuln_id=vid, title=pred.title, category=pred.category,
                        cwe_id=pred.cwe_id, severity=pred.severity, endpoint=pred.endpoint,
                        is_present=False,
                    ), is_fp=True)
                )
            continue

        eval_result = evaluate_single(pred, verdict)
        results.append(eval_result)

        if eval_result.is_tp:
            tp += 1
            verified_count += 1
        elif eval_result.is_fp:
            fp += 1
        elif eval_result.is_fn:
            fn += 1
        elif eval_result.is_tn:
            tn += 1

    total_predictions = len(predictions)
    precision = compute_precision(tp, fp)
    recall = compute_recall(tp, fn)
    f1 = compute_f1(precision, recall)
    verification_rate = compute_verification_rate(verified_count, total_predictions)
    # Clock skew / swapped args must never produce negative durations.
    assessment_time = max(0.0, (assessment_end - assessment_start).total_seconds())

    return BenchmarkScorecard(
        scan_id=scan_id,
        target=target,
        total_reference=len(unique_verdicts),
        total_predictions=total_predictions,
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=precision,
        recall=recall,
        f1=f1,
        verification_rate=verification_rate,
        assessment_time_s=assessment_time,
        results=[asdict(r) for r in results],
    )


def evaluate_benchmark(
    *,
    scan_id: str,
    target: str,
    predictions: dict[str, BenchmarkPrediction],
    verdicts: list[BenchmarkVerdict],
    assessment_start: datetime,
    assessment_end: datetime,
    output_path: Path | None = None,
) -> BenchmarkScorecard:
    """End-to-end Benchmark Protocol v2.0 evaluation with optional persistence."""
    scorecard = build_scorecard(
        scan_id=scan_id,
        target=target,
        predictions=predictions,
        verdicts=verdicts,
        assessment_start=assessment_start,
        assessment_end=assessment_end,
    )

    logger.info(
        "Benchmark v%s | TP=%d FP=%d FN=%d TN=%d | P=%.3f R=%.3f F1=%.3f VR=%.3f T=%.1fs",
        scorecard.protocol_version,
        scorecard.tp,
        scorecard.fp,
        scorecard.fn,
        scorecard.tn,
        scorecard.precision,
        scorecard.recall,
        scorecard.f1,
        scorecard.verification_rate,
        scorecard.assessment_time_s,
    )

    if output_path:
        scorecard.persist(output_path)

    return scorecard
