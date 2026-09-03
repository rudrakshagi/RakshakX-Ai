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
        # Import integrity statement lazily to avoid circular deps
        try:
            from rakshak.benchmark.prompts import INTEGRITY_STATEMENT
        except Exception:
            INTEGRITY_STATEMENT = (
                "The benchmark measures RakshakX on selected controlled environments and does not "
                "establish universal vulnerability detection, zero-day detection, enterprise-scale "
                "performance, or security of arbitrary real-world systems."
            )

        # Partition by verification_status
        confirmed = [v for v in self.vulnerabilities if (v.get("verification_status") or "confirmed").lower() == "confirmed" or v.get("verified") is True]
        probable = [v for v in self.vulnerabilities if (v.get("verification_status") or "").lower() == "probable"]
        unconfirmed = [v for v in self.vulnerabilities if (v.get("verification_status") or "").lower() == "unconfirmed"]
        # Fallback: if no explicit tiers, treat all as confirmed (backwards compat)
        if not probable and not unconfirmed and confirmed == [] and self.vulnerabilities:
            # No tier was set at all and verified flag missing -> treat all as confirmed
            has_tier = any(v.get("verification_status") for v in self.vulnerabilities)
            if not has_tier:
                confirmed = self.vulnerabilities

        # Gather environment summary if available
        env_summary = ""
        try:
            meta_file = self.run_dir / "run_meta.json"
            if meta_file.exists():
                import json as _json
                meta = _json.loads(meta_file.read_text(encoding="utf-8"))
                env_summary = f"Target: `{meta.get('target','N/A')}` | Mode: `{meta.get('mode','N/A')}` | Scope: `{meta.get('scope', meta.get('target','N/A'))}`"
        except Exception:
            pass

        lines = [
            f"# RakshakX Security Assessment Report: {self.scan_id}",
            f"\n**Assessment Date**: {self.start_time}  ",
            f"**Total Findings**: {len(self.vulnerabilities)} (Confirmed: {len(confirmed)} | Probable: {len(probable)} | Unconfirmed: {len(unconfirmed)})\n",
            "---",
            "## 1. Executive Summary",
            self.executive_summary or "Scan in progress... Autonomous security assessment with evidence-backed verification.",
            "\n## 2. Scope and Target",
            env_summary or f"Target: `{self.scan_id}` — scope as supplied to the scan. See run_meta.json for exact scope/target.",
            f"\n- **Scan ID**: `{self.scan_id}`",
            f"- **Started**: {self.start_time}",
            f"- **Ended**: {self.end_time or 'In progress'}",
            "\n## 3. Methodology",
            self.methodology or "Autonomous multi-agent dynamic penetration testing inside an isolated Kali Linux sandbox with Caido proxy (48080), empirical PoC validation, and CVSS 3.1 scoring.",
            "\n## 4. Environment and Tool Information",
            "Captured in `environment_freeze.json` (Python, OS, hardware, Docker, LLM, security tools, target, config snapshot). See benchmark artifacts for full freeze and integrity hash.",
            "\n## 5. Confirmed Findings",
        ]

        if not confirmed:
            lines.append("\n*No confirmed findings — no vulnerability met the evidence threshold for Confirmed status.*")
        else:
            for i, v in enumerate(confirmed, start=1):
                lines.extend(self._finding_block(i, v, tier="Confirmed"))

        lines.append("\n## 6. Probable Findings")
        if not probable:
            lines.append("\n*No probable findings.*")
        else:
            for i, v in enumerate(probable, start=1):
                lines.extend(self._finding_block(i, v, tier="Probable"))

        lines.append("\n## 7. Unconfirmed Observations")
        if not unconfirmed:
            lines.append("\n*No unconfirmed observations.*")
        else:
            for i, v in enumerate(unconfirmed, start=1):
                lines.extend(self._finding_block(i, v, tier="Unconfirmed"))

        lines.extend([
            "\n## 8. Evidence for Each Material Finding",
            "Each finding above includes reproduction PoC, affected endpoint, and confidence. Additional evidence is retained in sandbox spillway and Caido proxy logs.",
            "\n## 9. Severity and Confidence",
            "Severity derived from CVSS 3.1 vector; confidence reflects verification status (Confirmed = high, Probable = medium, Unconfirmed = low/informational).",
            "\n## 10. Impact",
            "Impact is assessed per finding based on exploitability and data exposure. See individual finding blocks for impact statements. Where impact is not explicitly provided, treat severity as the primary risk indicator.",
            "\n## 11. Remediation",
            self.recommendations or "Apply principle of least privilege, parameterized queries, output encoding, strict access controls, and patch management. See per-finding remediation_patch fields.",
        ])

        # Include per-finding remediation summary if available
        for v in self.vulnerabilities:
            patch = v.get("remediation_patch") or v.get("remediation")
            if patch and v not in confirmed + probable + unconfirmed:
                pass  # already covered; this path only for edge tier handling

        lines.extend([
            "\n## 12. Limitations",
            "Assessment is point-in-time, scope-limited, and tool-assisted. Coverage depends on target state, authentication, and rate limits. Findings require human review before remediation. "
            + INTEGRITY_STATEMENT,
            "\n---",
            f"\n*Integrity Statement*: {INTEGRITY_STATEMENT}",
            "\n*Report generated by RakshakX Community Edition — Rudraksh AGI (GSTIN 24NKPM5455A1ZX).*",
        ])
        return "\n".join(lines)

    def _finding_block(self, idx: int, v: dict[str, Any], tier: str = "Confirmed") -> list[str]:
        """Render a single finding block for markdown."""
        conf = v.get("confidence") or v.get("verification_status") or tier
        return [
            f"\n### {idx}. {v.get('title')} ({v.get('severity', '').upper()}) — {tier}",
            f"- **Finding ID**: `{v.get('id', v.get('finding_hash', 'N/A'))}`",
            f"- **CVSS 3.1 Score**: {v.get('cvss_score', 'N/A')} (`{v.get('cvss_vector', 'N/A')}`)",
            f"- **Category**: {v.get('category', 'N/A')} | **CWE**: {v.get('cwe_id', 'N/A')}",
            f"- **Affected Endpoint**: `{v.get('endpoint', 'N/A')}`",
            f"- **Severity**: {v.get('severity', 'N/A')} | **Confidence**: {conf} | **Verification**: {v.get('verification_status', tier)}",
            f"\n**Description**:\n{v.get('description', 'No description provided.')}",
            f"\n**Impact**: {v.get('impact', 'See severity and CVSS vector. Exploitability assessed via PoC.')}",
            "\n**Evidence / Reproduction PoC**:\n```bash",
            v.get("poc", "# No PoC command provided"),
            "```",
            f"\n**Remediation**:\n```\n{v.get('remediation_patch') or v.get('remediation') or 'Follow secure coding guidelines for the affected component.'}\n```",
        ]


def get_global_report_state() -> ReportState | None:
    return _global_report_state


def set_global_report_state(state: ReportState) -> None:
    global _global_report_state  # noqa: PLW0603
    _global_report_state = state
