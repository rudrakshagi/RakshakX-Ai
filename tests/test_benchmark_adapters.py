"""Tests for benchmark adapters and extended freeze."""

import json
from datetime import UTC, datetime
from pathlib import Path

from rakshak.benchmark.adapters import (
    evaluate_live_scan,
    load_ground_truth,
    vulnerabilities_to_predictions,
)
from rakshak.benchmark.metrics import BenchmarkVerdict
from rakshak.benchmark.prompts import INTEGRITY_STATEMENT, PROMPT_REGISTRY, get_prompt
from rakshak.benchmark.runner import freeze_environment


def test_prompt_registry_completeness() -> None:
    assert "T01" in PROMPT_REGISTRY
    assert "T04" in PROMPT_REGISTRY
    assert "A.1" in PROMPT_REGISTRY or "A1" in PROMPT_REGISTRY
    assert len(INTEGRITY_STATEMENT) > 20
    assert get_prompt("T01") is not None
    assert get_prompt("A.1") is not None
    assert get_prompt("deep") is None


def test_ground_truth_load() -> None:
    for name in ("juice_shop", "dvwa", "metasploitable2"):
        p = Path(f"rakshak/benchmark/targets/{name}.json")
        assert p.exists(), f"Missing {p}"
        verdicts = load_ground_truth(p)
        assert len(verdicts) >= 5
        assert all(isinstance(v, BenchmarkVerdict) for v in verdicts)


def test_vuln_to_prediction_matching() -> None:
    verdicts = [
        BenchmarkVerdict(vuln_id="JS-001", title="SQL Injection", category="sqli", cwe_id="CWE-89", severity="HIGH", endpoint="/rest/products/search", is_present=True),
        BenchmarkVerdict(vuln_id="JS-002", title="XSS", category="xss", cwe_id="CWE-79", severity="MEDIUM", endpoint="/#/search", is_present=True),
    ]
    vulns = [
        {"title": "SQL Injection in search", "category": "sqli", "cwe_id": "CWE-89", "severity": "HIGH", "endpoint": "/rest/products/search", "verified": True},
        {"title": "Totally unrelated FP", "category": "xss", "cwe_id": "CWE-999", "severity": "LOW", "endpoint": "/nope", "verified": True},
    ]
    preds = vulnerabilities_to_predictions(vulns, verdicts)
    # First should match JS-001, second is synthetic FP
    assert "JS-001" in preds
    assert preds["JS-001"].verified is True
    assert any(k.startswith("FP-SYNTH") for k in preds)


def test_live_scan_e2e(tmp_path: Path) -> None:
    gt = Path("rakshak/benchmark/targets/juice_shop.json")
    vulns = [
        {"title": "SQL Injection in /rest/products/search", "category": "sqli", "cwe_id": "CWE-89", "severity": "HIGH", "endpoint": "/rest/products/search", "verified": True},
        {"title": "Reflected XSS in search", "category": "xss", "cwe_id": "CWE-79", "severity": "MEDIUM", "endpoint": "/#/search", "verified": True},
    ]
    sc = evaluate_live_scan(
        scan_id="test-live",
        target="http://localhost:3001",
        vulnerabilities=vulns,
        ground_truth_path=gt,
        assessment_start=datetime.now(UTC),
        assessment_end=datetime.now(UTC),
        output_path=tmp_path / "scorecard.json",
    )
    assert sc.tp >= 1
    assert sc.precision > 0
    assert (tmp_path / "scorecard.json").exists()


def test_extended_freeze_fields(tmp_path: Path) -> None:
    freeze = freeze_environment(
        model="opencode/big-pickle",
        provider="opencode",
        rakshak_version="2.0-community",
        target_name="juice_shop",
        target_url="http://localhost:3001",
        prompt_verbatim="T01 prompt",
        scope="http://localhost:3001/",
        capture_hardware=True,
        capture_tools=False,  # faster in CI
    )
    assert freeze.hardware is not None
    assert freeze.target.name == "juice_shop"
    assert freeze.prompt_verbatim == "T01 prompt"
    assert freeze.scope == "http://localhost:3001/"
    assert freeze.inference in ("local", "cloud", "api")
    h = freeze.persist(tmp_path / "freeze.json")
    assert len(h) == 64
    data = json.loads((tmp_path / "freeze.json").read_text(encoding="utf-8"))
    assert "integrity_hash" in data
    assert "hardware" in data
    assert "security_tools" in data
