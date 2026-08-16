"""Unit tests for SARIF 2.1.0 report generation."""

from rakshak.report.sarif import generate_sarif_report


def test_generate_sarif_schema():
    findings = [
        {
            "title": "SQL Injection in User Login",
            "category": "Injection",
            "cwe_id": "CWE-89",
            "cvss_score": 9.8,
            "severity": "critical",
            "endpoint": "https://target.local/api/login",
            "poc": "curl -X POST ...",
            "remediation_patch": "Use parameterized queries.",
            "code_locations": [
                {
                    "file": "app/auth.py",
                    "start_line": 45,
                    "end_line": 48,
                    "snippet": "cursor.execute(f'SELECT * FROM users WHERE user={u}')",
                }
            ],
        }
    ]

    sarif = generate_sarif_report(findings, scan_id="test-scan-123", target="https://target.local")

    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "RakshakX"
    assert len(run["tool"]["driver"]["rules"]) == 1
    assert run["tool"]["driver"]["rules"][0]["id"] == "CWE-89"
    assert len(run["results"]) == 1
    assert run["results"][0]["level"] == "error"
    assert run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "app/auth.py"
