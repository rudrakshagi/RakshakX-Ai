"""Seed a realistic demo scan record to showcase the UI."""

import json
from pathlib import Path

def seed_demo():
    scan_id = "demo-scan-01"
    run_dir = Path("rakshak_runs") / scan_id
    state_dir = run_dir / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 1. Multi-Agent Graph Snapshot
    agents_data = {
        "names": {
            "root_01": "Root Orchestrator",
            "sub_jwt": "JWT Auth Specialist",
            "sub_sqli": "SQLi Exploit Prober",
            "sub_race": "Concurrency Specialist",
        },
        "statuses": {
            "root_01": "running",
            "sub_jwt": "completed",
            "sub_sqli": "completed",
            "sub_race": "running",
        },
        "parent_of": {
            "root_01": None,
            "sub_jwt": "root_01",
            "sub_sqli": "root_01",
            "sub_race": "root_01",
        },
        "metadata": {
            "root_01": {"task": "Map attack surface and delegate specialized probing."},
            "sub_jwt": {"task": "Probe /api/v1/auth for algorithm confusion and key traversal."},
            "sub_sqli": {"task": "Test /api/search and /api/catalog for blind SQL injection."},
            "sub_race": {"task": "Test /api/coupons/apply for concurrent double-redemption."},
        }
    }
    (state_dir / "agents.json").write_text(json.dumps(agents_data, indent=2), encoding="utf-8")

    # 2. Verified Vulnerabilities
    vulnerabilities = [
        {
            "title": "Authentication Bypass via JWT Algorithm Confusion (RS256 to HS256)",
            "category": "Broken Authentication",
            "cwe_id": "CWE-347",
            "cvss_score": 9.8,
            "severity": "critical",
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "endpoint": "https://target.app/api/v1/auth/verify",
            "description": "The backend JWT verification routine fails to enforce the RS256 algorithm constraint, allowing tokens signed with the server public key using HMAC-SHA256 (HS256) to be accepted as valid administrator sessions.",
            "poc": "jwt_tool eyJhbGciOiJSUzI1NiJ9... -X k -pk /workspace/public.pem\ncurl -H 'Authorization: Bearer eyJhbGciOiJIUzI1Ni...' https://target.app/api/v1/admin/users",
            "remediation_patch": "Explicitly whitelist allowed algorithms in JWT verification options: jwt.verify(token, key, { algorithms: ['RS256'] })",
            "code_locations": [
                {
                    "file": "src/auth/jwt_verifier.py",
                    "start_line": 24,
                    "end_line": 28,
                    "snippet": "decoded = jwt.decode(token, public_key) # missing algorithms parameter"
                }
            ]
        },
        {
            "title": "Time-Based Blind SQL Injection in Search API",
            "category": "Injection",
            "cwe_id": "CWE-89",
            "cvss_score": 8.5,
            "severity": "high",
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N",
            "endpoint": "https://target.app/api/v1/search?category=electronics",
            "description": "User input passed to the `category` query parameter is directly interpolated into a PostgreSQL SQL query without parameterization, enabling arbitrary database query injection.",
            "poc": "curl -s \"https://target.app/api/v1/search?category=electronics'%20OR%20pg_sleep(5)--%20-\"",
            "remediation_patch": "Use parameterized queries: cursor.execute('SELECT * FROM items WHERE category = %s', (category,))",
            "code_locations": [
                {
                    "file": "src/controllers/catalog.py",
                    "start_line": 62,
                    "end_line": 64,
                    "snippet": "query = f\"SELECT * FROM items WHERE category = '{cat}'\""
                }
            ]
        },
        {
            "title": "Race Condition in Single-Use Coupon Redemption",
            "category": "Broken Business Logic",
            "cwe_id": "CWE-362",
            "cvss_score": 5.3,
            "severity": "medium",
            "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:H/A:N",
            "endpoint": "https://target.app/api/v1/coupons/apply",
            "description": "The coupon redemption handler checks coupon usage status and updates the database in non-atomic operations, allowing 12 concurrent requests to successfully apply a single-use discount coupon multiple times.",
            "poc": "python3 /workspace/exploit_race.py --coupon SAVE50 --concurrency 20",
            "remediation_patch": "Enforce atomic database updates with SELECT ... FOR UPDATE or distributed Redis mutex locks.",
            "code_locations": []
        }
    ]
    (run_dir / "vulnerabilities.json").write_text(json.dumps(vulnerabilities, indent=2), encoding="utf-8")

    # 3. Generate Executive Markdown
    md_report = """# RakshakX Security Assessment Report: demo-scan-01

**Target**: `https://target.app`  
**Assessment Mode**: DEEP DYNAMIC PENTEST  
**Verified Vulnerabilities**: 3 Findings  

---

## 1. Executive Summary
RakshakX conducted an autonomous multi-agent penetration test against `https://target.app`. The assessment identified 1 Critical severity flaw (JWT Authentication Bypass), 1 High severity flaw (Time-based SQL Injection), and 1 Medium severity business logic flaw (Coupon Race Condition). All findings have been verified through dynamic proof-of-concept execution.

## 2. Methodology
The engine initialized an isolated Kali Linux sandbox, routed all network traffic through Caido HTTP proxy, and deployed specialized child agents to execute targeted exploit vectors.
"""
    (run_dir / "report.md").write_text(md_report, encoding="utf-8")

    # 4. Generate SARIF 2.1.0
    try:
        from rakshak.report.sarif import write_sarif_file
        write_sarif_file(vulnerabilities, run_dir / "sarif.json", scan_id=scan_id, target="https://target.app")
    except Exception as e:
        print(f"[!] SARIF generation skipped: {e}")

    # 5. Generate Styled PDF Report if reportlab is available
    try:
        from rakshak.report.pdf_writer import generate_pdf_report
        generate_pdf_report(
            scan_id=scan_id,
            target="https://target.app",
            vulnerabilities=vulnerabilities,
            executive_summary="Autonomous security assessment completed with 3 verified vulnerabilities.",
            methodology="Multi-agent dynamic testing inside isolated Kali Linux sandbox with transparent Caido proxy.",
            technical_analysis="Identified critical JWT algorithm confusion, SQL injection in search catalog, and coupon race condition.",
            recommendations="Implement algorithm pinning for JWTs, parameterized SQL queries, and atomic database locks for coupon redemption.",
            output_path=run_dir / "report.pdf",
        )
    except Exception as e:
        print(f"[!] PDF generation skipped (reportlab not installed on host): {e}")

    print(f"[+] Demo scan data seeded in: {run_dir}")

if __name__ == "__main__":
    seed_demo()
