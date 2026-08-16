"""Global report state and scan finding repository."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rakshak.report.dedupe import compute_vulnerability_hash
from rakshak.report.pdf_writer import generate_pdf_report
from rakshak.report.sarif import write_sarif_file

logger = logging.getLogger(__name__)

_global_report_state: ReportState | None = None


class ReportState:
    """Thread-safe state container tracking confirmed findings and executive narrative."""

    def __init__(self, scan_id: str, run_dir: Path) -> None:
        self.scan_id = scan_id
        self.run_dir = run_dir
        self.vulnerabilities: list[dict[str, Any]] = []
        self.seen_hashes: set[str] = set()
        self.executive_summary: str = ""
        self.methodology: str = ""
        self.technical_analysis: str = ""
        self.recommendations: str = ""
        self.start_time: str = datetime.now(UTC).isoformat()
        self.end_time: str | None = None

    def add_vulnerability(self, vuln: dict[str, Any]) -> bool:
        """Add a vulnerability finding, ignoring duplicates based on composite hash."""
        h = compute_vulnerability_hash(
            category=vuln.get("category", ""),
            endpoint=vuln.get("endpoint", ""),
            cwe_id=vuln.get("cwe_id", ""),
            title=vuln.get("title", ""),
        )
        if h in self.seen_hashes:
            logger.info("Skipping duplicate finding: %s (hash=%s)", vuln.get("title"), h)
            return False

        self.seen_hashes.add(h)
        vuln["finding_hash"] = h
        vuln["discovered_at"] = datetime.now(UTC).isoformat()
        self.vulnerabilities.append(vuln)
        self.persist()
        return True

    def update_final_narrative(
        self,
        *,
        executive_summary: str,
        methodology: str,
        technical_analysis: str,
        recommendations: str,
    ) -> None:
        self.executive_summary = executive_summary
        self.methodology = methodology
        self.technical_analysis = technical_analysis
        self.recommendations = recommendations
        self.end_time = datetime.now(UTC).isoformat()
        self.persist()

    def persist(self) -> None:
        """Write current findings, SARIF 2.1.0, and markdown reports to the scan directory."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        vuln_file = self.run_dir / "vulnerabilities.json"
        vuln_file.write_text(json.dumps(self.vulnerabilities, indent=2), encoding="utf-8")

        # Generate SARIF 2.1.0 report
        sarif_file = self.run_dir / "sarif.json"
        write_sarif_file(
            self.vulnerabilities,
            sarif_file,
            scan_id=self.scan_id,
            target=self.scan_id,
        )

        # Generate Executive Markdown Report
        md_content = self.render_markdown_report()
        (self.run_dir / "report.md").write_text(md_content, encoding="utf-8")

        # Generate Executive PDF Report
        try:
            generate_pdf_report(
                scan_id=self.scan_id,
                target=self.scan_id,
                vulnerabilities=self.vulnerabilities,
                executive_summary=self.executive_summary,
                methodology=self.methodology,
                technical_analysis=self.technical_analysis,
                recommendations=self.recommendations,
                output_path=self.run_dir / "report.pdf",
            )
        except Exception:
            logger.exception("Failed to write PDF report to %s", self.run_dir / "report.pdf")

    def render_markdown_report(self) -> str:
        lines = [
            f"# RakshakX Security Assessment Report: {self.scan_id}",
            f"\n**Assessment Date**: {self.start_time}  ",
            f"**Total Findings Verified**: {len(self.vulnerabilities)}\n",
            "---",
            "## 1. Executive Summary",
            self.executive_summary or "Scan in progress...",
            "\n## 2. Assessment Methodology",
            self.methodology or "Autonomous multi-agent dynamic pentesting...",
            "\n## 3. Technical Analysis",
            self.technical_analysis or "Details pending...",
            "\n## 4. Confirmed Vulnerability Findings",
        ]

        if not self.vulnerabilities:
            lines.append("\n*No vulnerabilities confirmed during this assessment.*")
        else:
            for i, v in enumerate(self.vulnerabilities, start=1):
                lines.extend([
                    f"\n### {i}. {v.get('title')} ({v.get('severity', '').upper()})",
                    f"- **CVSS 3.1 Score**: {v.get('cvss_score')} (`{v.get('cvss_vector')}`)",
                    f"- **Category**: {v.get('category')} | **CWE**: {v.get('cwe_id')}",
                    f"- **Affected Endpoint**: `{v.get('endpoint', 'N/A')}`",
                    f"\n**Description**:\n{v.get('description')}",
                    "\n**Reproduction PoC**:\n```bash",
                    v.get("poc", "# No PoC command provided"),
                    "```",
                ])

        lines.extend([
            "\n## 5. Strategic Recommendations",
            self.recommendations or "Remediation guidance pending...",
        ])
        return "\n".join(lines)


def get_global_report_state() -> ReportState | None:
    return _global_report_state


def set_global_report_state(state: ReportState) -> None:
    global _global_report_state  # noqa: PLW0603
    _global_report_state = state
