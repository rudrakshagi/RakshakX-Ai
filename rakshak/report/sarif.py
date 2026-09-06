"""SARIF 2.1.0 export engine for GitHub Code Scanning & CI/CD integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rakshak.report.severity import normalize_severity


def _cvss_to_sarif_level(severity: str) -> str:
    """Map canonical severity strings to SARIF rule default levels."""
    sev = normalize_severity(severity)
    if sev in ("critical", "high"):
        return "error"
    if sev == "medium":
        return "warning"
    return "note"


def generate_sarif_report(
    vulnerabilities: list[dict[str, Any]],
    *,
    scan_id: str,
    target: str,
) -> dict[str, Any]:
    """Compile verified vulnerability findings into the standard OASIS SARIF 2.1.0 schema."""
    rules: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    seen_rule_ids: set[str] = set()

    for vuln in vulnerabilities:
        rule_id = vuln.get("cwe_id") or "CWE-Unknown"
        title = vuln.get("title", "Security Vulnerability")
        severity = normalize_severity(vuln.get("severity", "medium"))
        sarif_level = _cvss_to_sarif_level(severity)

        if rule_id not in seen_rule_ids:
            seen_rule_ids.add(rule_id)
            rules.append({
                "id": rule_id,
                "name": rule_id.replace("-", "_"),
                "shortDescription": {"text": title},
                "fullDescription": {"text": vuln.get("description", title)},
                "defaultConfiguration": {"level": sarif_level},
                "properties": {
                    "tags": ["security", vuln.get("category", "OWASP")],
                    "precision": "high",
                    "problem.severity": sarif_level,
                    "security-severity": str(vuln.get("cvss_score", "5.0")),
                },
            })

        # Physical location mapping if source files were identified
        locations: list[dict[str, Any]] = []
        for loc in vuln.get("code_locations", []):
            file_path = loc.get("file")
            start_line = loc.get("start_line", 1)
            if file_path:
                locations.append({
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_path},
                        "region": {
                            "startLine": start_line,
                            "endLine": loc.get("end_line", start_line),
                            "snippet": {"text": loc.get("snippet", "")},
                        },
                    }
                })

        # Fallback to logical endpoint location if no source code file
        if not locations:
            endpoint = vuln.get("endpoint") or target
            locations.append({
                "logicalLocations": [{
                    "name": endpoint,
                    "kind": "endpoint",
                }]
            })

        results.append({
            "ruleId": rule_id,
            "level": sarif_level,
            "message": {
                "text": f"{title} (CVSS {vuln.get('cvss_score', 'N/A')} {severity.upper()})\n\n"
                        f"PoC:\n{vuln.get('poc', 'N/A')}\n\n"
                        f"Remediation:\n{vuln.get('remediation_patch', 'Follow secure coding guidelines.')}"
            },
            "locations": locations,
        })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "RakshakX",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/rakshakx/rakshakx",
                        "rules": rules,
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "toolExecutionNotifications": [],
                    }
                ],
                "results": results,
            }
        ],
    }


def write_sarif_file(
    vulnerabilities: list[dict[str, Any]],
    output_path: Path,
    *,
    scan_id: str,
    target: str,
) -> None:
    """Serialize SARIF report to disk."""
    sarif_data = generate_sarif_report(vulnerabilities, scan_id=scan_id, target=target)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sarif_data, indent=2), encoding="utf-8")
