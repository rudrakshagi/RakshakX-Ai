"""Phase-5 report+benchmark harness (no docker, no network, no LLM)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rakshak.benchmark.adapters import vulnerabilities_to_predictions
from rakshak.benchmark.metrics import (
    BenchmarkPrediction,
    BenchmarkVerdict,
    build_scorecard,
    coerce_verified,
    evaluate_single,
)
from rakshak.benchmark.runner import RakshakEnvironmentFreeze, verify_environment_freeze
from rakshak.report.sarif import _cvss_to_sarif_level, generate_sarif_report
from rakshak.report.severity import is_actionable, normalize_severity, severity_rank


# ------------------------------------------------------------------
# 1. normalize_severity
# ------------------------------------------------------------------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Critical", "critical"),
        ("HIGH", "high"),
        ("Moderate", "medium"),
        ("med", "medium"),
        ("NONE", "informational"),
        ("none", "informational"),
        ("", "informational"),
        (None, "informational"),
        ("unknown", "informational"),
        ("info", "informational"),
        ("N/A", "informational"),
        ("  High  ", "high"),
        (12345, "informational"),
        ("garbage-sev-xyz", "informational"),
        ("crit", "critical"),
        ("low", "low"),
        ("LOW", "low"),
    ],
)
def test_normalize_severity_parametrized(raw, expected) -> None:
    out = normalize_severity(raw)
    assert out == expected
    assert out != ""  # never empty


def test_normalize_never_raises_never_empty() -> None:
    for weird in (None, "", "   ", 0, 12345, 3.14, ["high"], {"a": 1}, object()):
        out = normalize_severity(weird)
        assert isinstance(out, str) and out != ""


def test_severity_rank_ordering() -> None:
    assert severity_rank("critical") > severity_rank("high")
    assert severity_rank("high") > severity_rank("medium")
    assert severity_rank("medium") > severity_rank("low")
    assert severity_rank("low") > severity_rank("informational")


def test_is_actionable() -> None:
    for sev in ("critical", "high", "medium", "low", "Critical"):
        assert is_actionable(sev) is True
    assert is_actionable("informational") is False
    assert is_actionable("none") is False
    assert is_actionable("") is False


# ------------------------------------------------------------------
# 2. SARIF
# ------------------------------------------------------------------

@pytest.mark.parametrize(
    ("severity", "expected_level"),
    [
        ("critical", "error"),
        ("high", "error"),
        ("medium", "warning"),
        ("low", "note"),
        ("none", "note"),
        ("", "note"),
        ("Critical", "error"),  # canonicalized first
    ],
)
def test_sarif_level_mapping(severity, expected_level) -> None:
    assert _cvss_to_sarif_level(severity) == expected_level


def _sarif_msg_level(severity: str) -> tuple[str, str]:
    sarif = generate_sarif_report(
        [{
            "title": "T", "category": "Injection", "cwe_id": "CWE-89",
            "cvss_score": 5.0, "severity": severity, "endpoint": "/e",
            "poc": "p", "remediation_patch": "r",
        }],
        scan_id="s", target="t",
    )
    res = sarif["runs"][0]["results"][0]
    return res["level"], res["message"]["text"]


def test_sarif_message_canonical_uppercase_no_none() -> None:
    cases = [
        ("critical", "error", "CRITICAL"),
        ("high", "error", "HIGH"),
        ("medium", "warning", "MEDIUM"),
        ("low", "note", "LOW"),
        ("none", "note", "INFORMATIONAL"),
        ("", "note", "INFORMATIONAL"),
        ("Critical", "error", "CRITICAL"),
    ]
    for sev, level, canon in cases:
        got_level, msg = _sarif_msg_level(sev)
        assert got_level == level, sev
        assert canon in msg, (sev, msg)
        assert "NONE" not in msg, (sev, msg)


# ------------------------------------------------------------------
# 3. metrics
# ------------------------------------------------------------------

def _verdict(vuln_id: str = "V-1") -> BenchmarkVerdict:
    return BenchmarkVerdict(
        vuln_id=vuln_id, title="SQLi", category="sqli", cwe_id="CWE-89",
        severity="HIGH", endpoint="/api", is_present=True,
    )


def _pred_with_raw_verified(raw) -> BenchmarkPrediction:
    # Bypass __init__ type expectations: construct then overwrite to simulate
    # raw JSON-ish values flowing in (post_init also coerces, which is the point).
    p = BenchmarkPrediction(
        vuln_id="V-1", title="SQLi", category="sqli", cwe_id="CWE-89",
        severity="HIGH", endpoint="/api", verified=False,
    )
    p.verified = raw  # simulate un-coerced caller value
    return p


@pytest.mark.parametrize(
    ("raw", "expect_tp"),
    [
        ("false", False),
        ("False", False),
        ("true", True),
        ("True", True),
        (1, True),
        ("yes", True),
        (0, False),
        ("", False),
    ],
)
def test_evaluate_single_verified_coercion(raw, expect_tp) -> None:
    res = evaluate_single(_pred_with_raw_verified(raw), _verdict())
    if expect_tp:
        assert res.is_tp and not res.is_fn
    else:
        assert res.is_fn and not res.is_tp


def test_post_init_coerces_string_false() -> None:
    p = BenchmarkPrediction(
        vuln_id="V-1", title="T", category="c", cwe_id="CWE-1",
        severity="HIGH", endpoint="/e", verified="false",  # type: ignore[arg-type]
    )
    assert p.verified is False
    assert coerce_verified("false") is False
    assert coerce_verified("true") is True


def test_duplicate_verdict_ids_first_wins_warning(caplog) -> None:
    v1 = BenchmarkVerdict(vuln_id="DUP", title="First", category="c",
                          cwe_id="CWE-1", severity="HIGH", endpoint="/a", is_present=True)
    v2 = BenchmarkVerdict(vuln_id="DUP", title="Second", category="c",
                          cwe_id="CWE-1", severity="LOW", endpoint="/b", is_present=True)
    start = datetime.now(UTC)
    end = datetime.now(UTC)
    with caplog.at_level(logging.WARNING):
        sc = build_scorecard(
            scan_id="s", target="t", predictions={},
            verdicts=[v1, v2], assessment_start=start, assessment_end=end,
        )
    assert sc.total_reference == 1  # uniques, not 2
    assert any("Duplicate ground-truth vuln_id DUP" in r.message for r in caplog.records)
    assert sc.results[0]["verdict"]["title"] == "First"  # first wins


def test_assessment_time_clamped() -> None:
    start = datetime.now(UTC)
    end_earlier = datetime(2000, 1, 1, tzinfo=UTC)
    sc = build_scorecard(
        scan_id="s", target="t", predictions={}, verdicts=[_verdict()],
        assessment_start=start, assessment_end=end_earlier,
    )
    assert sc.assessment_time_s == 0


def test_empty_verdicts_empty_predictions() -> None:
    now = datetime.now(UTC)
    sc = build_scorecard(
        scan_id="s", target="t", predictions={}, verdicts=[],
        assessment_start=now, assessment_end=now,
    )
    assert (sc.precision, sc.recall, sc.f1) == (0.0, 0.0, 0.0)
    assert (sc.tp, sc.fp, sc.fn, sc.tn) == (0, 0, 0, 0)
    assert sc.total_reference == 0


# ------------------------------------------------------------------
# 4. adapters
# ------------------------------------------------------------------

def test_adapters_matched_severity_normalized() -> None:
    verdicts = [BenchmarkVerdict(
        vuln_id="V-1", title="SQL Injection", category="sqli",
        cwe_id="CWE-89", severity="HIGH", endpoint="/rest/products/search",
        is_present=True,
    )]
    vulns = [{
        "title": "SQL Injection in search", "category": "sqli", "cwe_id": "CWE-89",
        "severity": "Critical", "endpoint": "/rest/products/search", "verified": True,
    }]
    preds = vulnerabilities_to_predictions(vulns, verdicts)
    assert "V-1" in preds
    assert preds["V-1"].severity == "critical"


def test_adapters_unmatched_fp_synth_normalized() -> None:
    verdicts = [BenchmarkVerdict(
        vuln_id="V-1", title="SQL Injection", category="sqli",
        cwe_id="CWE-89", severity="HIGH", endpoint="/rest/products/search",
        is_present=True,
    )]
    vulns = [{
        "title": "zzz qqq www", "category": "nope-cat", "cwe_id": "CWE-999",
        "severity": "NONE", "endpoint": "/nope-nothing-here", "verified": True,
    }]
    preds = vulnerabilities_to_predictions(vulns, verdicts)
    synth = [k for k in preds if k.startswith("FP-SYNTH")]
    assert len(synth) == 1
    assert preds[synth[0]].severity == "informational"


# ------------------------------------------------------------------
# 5. freeze verify
# ------------------------------------------------------------------

def test_freeze_verify_roundtrip(tmp_path: Path) -> None:
    freeze = RakshakEnvironmentFreeze()  # direct: no pip/docker shell-outs
    fp = tmp_path / "freeze.json"
    freeze.persist(fp)
    ok, detail = verify_environment_freeze(fp)
    assert ok is True
    assert detail != ""


def test_freeze_verify_tampered(tmp_path: Path) -> None:
    fp = tmp_path / "freeze.json"
    RakshakEnvironmentFreeze().persist(fp)
    text = fp.read_text(encoding="utf-8")
    data = json.loads(text)
    assert "integrity_hash" in data
    # Tamper a body field, keep the stored hash
    tampered = text.replace('"freeze_version": "2.0"', '"freeze_version": "9.9"', 1)
    if tampered == text:  # fallback: flip an arbitrary body char
        tampered = text.replace('"2.0"', '"9.9"', 1)
    assert tampered != text
    fp.write_text(tampered, encoding="utf-8")
    ok, detail = verify_environment_freeze(fp)
    assert ok is False
    assert "mismatch" in detail.lower()


def test_freeze_verify_missing_hash(tmp_path: Path) -> None:
    fp = tmp_path / "freeze.json"
    fp.write_text(json.dumps({"freeze_version": "2.0"}), encoding="utf-8")
    ok, _ = verify_environment_freeze(fp)
    assert ok is False


def test_freeze_verify_corrupt_json(tmp_path: Path) -> None:
    fp = tmp_path / "freeze.json"
    fp.write_text("{not valid json!!!", encoding="utf-8")
    ok, _ = verify_environment_freeze(fp)
    assert ok is False


def test_freeze_verify_missing_file(tmp_path: Path) -> None:
    ok, _ = verify_environment_freeze(tmp_path / "does-not-exist.json")
    assert ok is False


# ------------------------------------------------------------------
# 6. reporting funnel
# ------------------------------------------------------------------

def test_reporting_funnel_zero_cvss_normalizes() -> None:
    from rakshak.tools.reporting.tool import _calculate_cvss

    zero_metrics = {
        "attack_vector": "P", "attack_complexity": "H",
        "privileges_required": "H", "user_interaction": "R",
        "scope": "U", "confidentiality": "N",
        "integrity": "N", "availability": "N",
    }
    score, severity, _vector = _calculate_cvss(zero_metrics)
    assert score == 0.0
    assert normalize_severity(severity) == "informational"


def test_reporting_tool_wires_normalizer() -> None:
    import rakshak.tools.reporting.tool as reporting_tool

    assert reporting_tool.normalize_severity is normalize_severity
