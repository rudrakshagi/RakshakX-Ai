"""Vulnerability finding submission tools with CVSS 3.1 validation."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from agents import RunContextWrapper, function_tool
from cvss import CVSS3

logger = logging.getLogger(__name__)

_CVSS_VALID = {
    "attack_vector": ["N", "A", "L", "P"],
    "attack_complexity": ["L", "H"],
    "privileges_required": ["N", "L", "H"],
    "user_interaction": ["N", "R"],
    "scope": ["U", "C"],
    "confidentiality": ["N", "L", "H"],
    "integrity": ["N", "L", "H"],
    "availability": ["N", "L", "H"],
}


def _calculate_cvss(breakdown: dict[str, str]) -> tuple[float, str, str]:
    """Compute base score, severity, and vector string from metrics."""
    vector = (
        f"CVSS:3.1/AV:{breakdown['attack_vector']}/AC:{breakdown['attack_complexity']}/"
        f"PR:{breakdown['privileges_required']}/UI:{breakdown['user_interaction']}/"
        f"S:{breakdown['scope']}/C:{breakdown['confidentiality']}/"
        f"I:{breakdown['integrity']}/A:{breakdown['availability']}"
    )
    cvss = CVSS3(vector)
    score = float(cvss.scores()[0])
    severity = cvss.severities()[0].lower()
    return score, severity, vector


@function_tool(timeout=60, strict_mode=False)
async def create_vulnerability_report(
    ctx: RunContextWrapper,
    title: Annotated[str, "Concise title for the vulnerability finding."],
    description: Annotated[str, "Detailed technical description of the vulnerability and impact."],
    category: Annotated[str, "Vulnerability category, e.g. 'SQL Injection', 'XSS', 'IDOR'."],
    cwe_id: Annotated[str, "CWE identifier, e.g. 'CWE-89'."],
    cvss_metrics: Annotated[
        dict[str, str],
        "CVSS 3.1 breakdown: attack_vector, attack_complexity, privileges_required, user_interaction, scope, confidentiality, integrity, availability.",
    ],
    reproduction_steps: Annotated[list[str], "Ordered, reproducible steps (with the exact PoC command) to confirm the finding."],
    exploit_poc: Annotated[str, "Reproducible proof-of-concept payload or command that triggered the vulnerability."],
    affected_endpoint: Annotated[str | None, "Target endpoint or URL where the finding was confirmed."] = None,
    code_locations: Annotated[list[dict[str, Any]] | None, "Optional source code locations (file/line) relevant to the finding."] = None,
    remediation_patch: Annotated[str | None, "Optional recommended remediation or patch guidance."] = None,
) -> str:
    """Register a confirmed, PoC-verified vulnerability finding.

    cvss_metrics requires keys: attack_vector (N/A/L/P), attack_complexity (L/H),
    privileges_required (N/L/H), user_interaction (N/R), scope (U/C),
    confidentiality (N/L/H), integrity (N/L/H), availability (N/L/H).
    """
    # Validate CVSS inputs
    for key, allowed in _CVSS_VALID.items():
        val = cvss_metrics.get(key)
        if val not in allowed:
            return json.dumps({
                "success": False,
                "error": f"Invalid CVSS metric '{key}': got '{val}', expected one of {allowed}",
            })

    try:
        score, severity, vector = _calculate_cvss(cvss_metrics)
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Failed to compute CVSS 3.1: {exc}"})

    finding_record = {
        "title": title,
        "description": description,
        "category": category,
        "cwe_id": cwe_id,
        "cvss_score": score,
        "severity": severity,
        "cvss_vector": vector,
        "endpoint": affected_endpoint or "",
        "reproduction_steps": reproduction_steps,
        "poc": exploit_poc,
        "code_locations": code_locations or [],
        "remediation_patch": remediation_patch or "",
    }

    # Register in global report state
    from rakshak.report.state import get_global_report_state
    report_state = get_global_report_state()
    if report_state is not None:
        report_state.add_vulnerability(finding_record)

    logger.info("Filed vulnerability report '%s' (CVSS %.1f, %s)", title, score, severity)
    return json.dumps({
        "success": True,
        "status": "finding_recorded",
        "title": title,
        "cvss_score": score,
        "severity": severity,
        "cvss_vector": vector,
    })
