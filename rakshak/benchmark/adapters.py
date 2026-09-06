"""Adapters: vulnerabilities.json -> BenchmarkPrediction and live scoring."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rakshak.benchmark.metrics import (
    BenchmarkPrediction,
    BenchmarkVerdict,
    evaluate_benchmark,
)
from rakshak.report.dedupe import normalize_endpoint
from rakshak.report.severity import normalize_severity

# ------------------------------------------------------------------
# Ground-truth loader
# ------------------------------------------------------------------

def load_ground_truth(path: Path) -> list[BenchmarkVerdict]:
    """Load verdicts from a benchmark target JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("ground_truth", data if isinstance(data, list) else [])
    verdicts: list[BenchmarkVerdict] = []
    for item in items:
        verdicts.append(BenchmarkVerdict(
            vuln_id=item["vuln_id"],
            title=item.get("title", ""),
            category=item.get("category", ""),
            cwe_id=item.get("cwe_id", ""),
            severity=normalize_severity(item.get("severity", "MEDIUM")),
            endpoint=item.get("endpoint", ""),
            is_present=item.get("is_present", True),
        ))
    return verdicts


def load_target_meta(path: Path) -> dict[str, Any]:
    """Load target meta (name/version/image/digest) from JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "target" in data:
            return {
                "name": data.get("target", ""),
                "version": data.get("version", ""),
                "image": data.get("image", ""),
                "digest": data.get("digest", ""),
            }
    except Exception:
        pass
    return {}


# ------------------------------------------------------------------
# Endpoint normalization + matching
# ------------------------------------------------------------------

def _norm_endpoint(ep: str) -> str:
    try:
        return normalize_endpoint(ep)
    except Exception:
        return ep.strip().lower().rstrip("/")


def _cwe_match(pred_cwe: str, verdict_cwe: str) -> bool:
    return pred_cwe.strip().upper() == verdict_cwe.strip().upper() and pred_cwe != ""


def _category_match(pred_cat: str, verdict_cat: str) -> bool:
    return pred_cat.strip().lower() == verdict_cat.strip().lower() and pred_cat != ""


def _endpoint_match(pred_ep: str, verdict_ep: str) -> bool:
    if not pred_ep or not verdict_ep:
        return False
    n_pred = _norm_endpoint(pred_ep)
    n_verd = _norm_endpoint(verdict_ep)
    if n_pred == n_verd:
        return True
    # Guard: root "/" normalized endpoints must not match non-root via substring
    if n_pred in ("/", "") or n_verd in ("/", ""):
        return False
    # substring containment after normalization (require len > 3 to avoid trivial "/")
    if len(n_pred) > 3 and len(n_verd) > 3 and (n_pred in n_verd or n_verd in n_pred):
        return True
    # loose: share last path segment (require segment len >= 3)
    pred_last = n_pred.rstrip("/").split("/")[-1] if "/" in n_pred else n_pred
    verd_last = n_verd.rstrip("/").split("/")[-1] if "/" in n_verd else n_verd
    return bool(pred_last and verd_last and len(pred_last) >= 3 and len(verd_last) >= 3 and pred_last == verd_last)


def _match_score(pred: dict[str, Any], verdict: BenchmarkVerdict) -> float:
    """Compute 0-1 match score between a vuln dict and a verdict."""
    score = 0.0
    weights = {"cwe": 0.4, "endpoint": 0.35, "category": 0.25}
    if _cwe_match(pred.get("cwe_id", ""), verdict.cwe_id):
        score += weights["cwe"]
    if _category_match(pred.get("category", ""), verdict.category):
        score += weights["category"]
    if _endpoint_match(pred.get("endpoint", ""), verdict.endpoint):
        score += weights["endpoint"]
    # title keyword overlap bonus (up to 0.15, capped at 1.0)
    title_pred = pred.get("title", "").lower()
    title_verd = verdict.title.lower()
    if title_pred and title_verd:
        pred_words = set(re.findall(r"\w{3,}", title_pred))
        verd_words = set(re.findall(r"\w{3,}", title_verd))
        if pred_words and verd_words:
            overlap = len(pred_words & verd_words) / max(len(verd_words), 1)
            score += min(0.15, overlap * 0.3)
    return min(1.0, round(score, 3))


# ------------------------------------------------------------------
# vulnerabilities.json -> predictions
# ------------------------------------------------------------------

def vulnerabilities_to_predictions(
    vulnerabilities: list[dict[str, Any]],
    verdicts: list[BenchmarkVerdict],
    *,
    match_threshold: float = 0.5,
) -> dict[str, BenchmarkPrediction]:
    """
    Convert live findings to BenchmarkPredictions by best-matching each
    finding to a ground-truth verdict. Unmatched findings become FP entries
    with synthetic vuln_ids.
    """
    verdict_by_id = {v.vuln_id: v for v in verdicts}
    predictions: dict[str, BenchmarkPrediction] = {}
    used_verdict_ids: set[str] = set()

    for idx, vuln in enumerate(vulnerabilities):
        # Determine verification: respect verification_status / verified / confidence
        vs = (vuln.get("verification_status") or vuln.get("confidence") or "").lower()
        verified = vuln.get("verified", False)
        if isinstance(verified, str):
            verified = verified.lower() in ("true", "verified", "confirmed")
        if not verified:
            # treat Confirmed/verified as verified
            verified = vs in ("confirmed", "verified", "high")
            # also treat explicit 'verified: true' already handled
            if vuln.get("verification_status", "").lower() == "confirmed":
                verified = True

        # Find best matching verdict
        best_id: str | None = None
        best_score = 0.0
        for vid, verdict in verdict_by_id.items():
            if vid in used_verdict_ids:
                continue
            s = _match_score(vuln, verdict)
            if s > best_score:
                best_score = s
                best_id = vid

        if best_id is not None and best_score >= match_threshold:
            verdict = verdict_by_id[best_id]
            used_verdict_ids.add(best_id)
            predictions[best_id] = BenchmarkPrediction(
                vuln_id=best_id,
                title=vuln.get("title", verdict.title),
                category=vuln.get("category", verdict.category),
                cwe_id=vuln.get("cwe_id", verdict.cwe_id),
                severity=normalize_severity(vuln.get("severity", verdict.severity)),
                endpoint=vuln.get("endpoint", verdict.endpoint),
                verified=bool(verified),
                match_score=best_score,
            )
        else:
            # Unmatched -> synthetic FP id
            synth_id = f"FP-SYNTH-{idx+1:03d}"
            # avoid collision with real ids
            while synth_id in predictions or synth_id in verdict_by_id:
                synth_id = f"FP-SYNTH-{idx+1:03d}-{len(predictions)}"
            predictions[synth_id] = BenchmarkPrediction(
                vuln_id=synth_id,
                title=vuln.get("title", f"Unmatched finding {idx+1}"),
                category=vuln.get("category", "unknown"),
                cwe_id=vuln.get("cwe_id", "CWE-Unknown"),
                severity=normalize_severity(vuln.get("severity", "MEDIUM")),
                endpoint=vuln.get("endpoint", ""),
                verified=bool(verified),
                match_score=best_score,
            )

    return predictions


# ------------------------------------------------------------------
# End-to-end live evaluation helper
# ------------------------------------------------------------------

def evaluate_live_scan(
    *,
    scan_id: str,
    target: str,
    vulnerabilities: list[dict[str, Any]],
    ground_truth_path: Path,
    assessment_start: datetime | None = None,
    assessment_end: datetime | None = None,
    output_path: Path | None = None,
) -> Any:
    """Evaluate a live scan's vulnerabilities against a ground-truth file."""
    verdicts = load_ground_truth(ground_truth_path)
    predictions = vulnerabilities_to_predictions(vulnerabilities, verdicts)
    start = assessment_start or datetime.now(UTC)
    end = assessment_end or datetime.now(UTC)
    return evaluate_benchmark(
        scan_id=scan_id,
        target=target,
        predictions=predictions,
        verdicts=verdicts,
        assessment_start=start,
        assessment_end=end,
        output_path=output_path,
    )
