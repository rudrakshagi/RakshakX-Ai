"""Unit tests for CVSS reporting tool."""

from __future__ import annotations

import json

from rakshak.tools.reporting.tool import create_vulnerability_report
from tests.conftest import invoke_tool

VALID_METRICS = {
    "attack_vector": "N",
    "attack_complexity": "L",
    "privileges_required": "N",
    "user_interaction": "N",
    "scope": "U",
    "confidentiality": "H",
    "integrity": "H",
    "availability": "H",
}


def test_valid_metrics_succeeds():
    import asyncio

    res = asyncio.run(invoke_tool(
        create_vulnerability_report,
        {},
        title="SQLi",
        description="desc",
        category="injection",
        cwe_id="CWE-89",
        cvss_metrics=VALID_METRICS,
        reproduction_steps=["step"],
        exploit_poc="curl",
    ))
    payload = json.loads(res)
    assert payload["success"] is True
    assert payload["cvss_score"] > 0
    assert payload["severity"] in ("none", "low", "medium", "high", "critical")


def test_invalid_metric_returns_error():
    import asyncio

    bad = dict(VALID_METRICS, attack_vector="Z")
    res = asyncio.run(invoke_tool(
        create_vulnerability_report,
        {},
        title="x",
        description="y",
        category="c",
        cwe_id="CWE-1",
        cvss_metrics=bad,
        reproduction_steps=[],
        exploit_poc="",
    ))
    payload = json.loads(res)
    assert payload["success"] is False
    assert "Invalid CVSS metric" in payload["error"]
