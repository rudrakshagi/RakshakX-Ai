"""Executive PDF report generation using ReportLab."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from html import escape as _html_escape
from pathlib import Path
from typing import Any

from rakshak.report.severity import normalize_severity

logger = logging.getLogger(__name__)


def _t(value: Any) -> str:
    """Escape finding/narrative text for ReportLab Paragraph markup.

    PoCs and titles routinely contain raw `<script>` tags — unescaped, the
    ParaParser aborts the whole PDF with "parse ended with N unclosed tags".
    """
    if value is None:
        return ""
    return _html_escape(str(value), quote=False)


INTEGRITY_STATEMENT_PDF = (
    "The benchmark measures RakshakX on selected controlled environments and does not "
    "establish universal vulnerability detection, zero-day detection, enterprise-scale "
    "performance, or security of arbitrary real-world systems."
)


def generate_pdf_report(
    *,
    scan_id: str,
    target: str,
    vulnerabilities: list[dict[str, Any]],
    executive_summary: str = "",
    methodology: str = "",
    technical_analysis: str = "",
    recommendations: str = "",
    output_path: Path,
) -> Path | None:
    """Generate a styled PDF pentest report."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        logger.warning("ReportLab library not installed on host. PDF generation skipped.")
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#b91c1c"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )
    code_style = ParagraphStyle(
        "CodeSnippet",
        parent=styles["Code"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=8,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("RakshakX Security Assessment Report", title_style))
    story.append(Paragraph(f"<b>Target:</b> {target} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Scan ID:</b> {scan_id}", body_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#b91c1c"), spaceAfter=15))

    # Findings Summary Metric Cards (normalized: "Critical"/"NONE"/"" all count)
    crit = sum(1 for v in vulnerabilities if normalize_severity(v.get("severity")) == "critical")
    high = sum(1 for v in vulnerabilities if normalize_severity(v.get("severity")) == "high")
    med = sum(1 for v in vulnerabilities if normalize_severity(v.get("severity")) == "medium")
    low = sum(1 for v in vulnerabilities if normalize_severity(v.get("severity")) == "low")

    metrics_data = [
        [
            Paragraph(f"<font color='#dc2626'><b>CRITICAL: {crit}</b></font>", body_style),
            Paragraph(f"<font color='#ea580c'><b>HIGH: {high}</b></font>", body_style),
            Paragraph(f"<font color='#d97706'><b>MEDIUM: {med}</b></font>", body_style),
            Paragraph(f"<font color='#2563eb'><b>LOW: {low}</b></font>", body_style),
            Paragraph(f"<b>TOTAL: {len(vulnerabilities)}</b>", body_style),
        ]
    ]
    t = Table(metrics_data, colWidths=[105, 105, 105, 105, 105])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary", h2_style))
    story.append(Paragraph(_t(executive_summary) or "Autonomous security assessment completed with dynamic verification.", body_style))
    story.append(Spacer(1, 10))

    # 2. Scope and Target
    story.append(Paragraph("2. Scope and Target", h2_style))
    story.append(Paragraph(f"Target: {target} &nbsp;|&nbsp; Scan ID: {scan_id} &nbsp;|&nbsp; Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style))
    story.append(Spacer(1, 8))

    # 3. Methodology
    story.append(Paragraph("3. Assessment Methodology", h2_style))
    story.append(Paragraph(_t(methodology) or "Conducted dynamic multi-agent probing inside an isolated Kali Linux sandbox.", body_style))
    if technical_analysis:
        story.append(Paragraph(_t(technical_analysis), body_style))
    story.append(Spacer(1, 10))

    # 4. Environment and Tool Information
    story.append(Paragraph("4. Environment and Tool Information", h2_style))
    story.append(Paragraph("Captured in environment_freeze.json (Python, OS, hardware, Docker, LLM, security tools, target, config). See benchmark artifacts for full freeze and integrity hash.", body_style))
    story.append(Spacer(1, 10))

    # Partition findings by tier
    confirmed = [v for v in vulnerabilities if (v.get("verification_status") or "confirmed").lower() == "confirmed" or (not v.get("verification_status") and v.get("verified") is not False)]
    probable = [v for v in vulnerabilities if (v.get("verification_status") or "").lower() == "probable"]
    unconfirmed = [v for v in vulnerabilities if (v.get("verification_status") or "").lower() == "unconfirmed"]
    has_tier = any(v.get("verification_status") for v in vulnerabilities)
    if not has_tier and vulnerabilities:
        # backwards compat: treat all as confirmed if no tier set
        confirmed = vulnerabilities
        probable = []
        unconfirmed = []

    def _add_tier(title_text: str, tier_vulns: list[dict[str, Any]]) -> None:
        story.append(Paragraph(title_text, h2_style))
        if not tier_vulns:
            story.append(Paragraph("<i>None in this tier.</i>", body_style))
            story.append(Spacer(1, 6))
            return
        for idx, v in enumerate(tier_vulns, start=1):
            title = _t(v.get("title", "Untitled Vulnerability"))
            sev = _t(normalize_severity(v.get("severity", "medium"))).upper()
            score = _t(v.get("cvss_score", "N/A"))
            ep = _t(v.get("endpoint", "N/A"))
            desc = _t(v.get("description", "No description provided."))
            poc = _t(v.get("poc", "# No PoC provided"))
            vs = _t(v.get("verification_status", "Confirmed"))
            conf = _t(v.get("confidence", v.get("verification_status", "Confirmed")))
            story.append(Paragraph(f"<b>{idx}. {title}</b> — <font color='#b91c1c'><b>{sev} (CVSS {score})</b></font> — {vs}", h2_style))
            story.append(Paragraph(f"<b>Affected:</b> <code>{ep}</code> &nbsp;|&nbsp; <b>CWE:</b> {_t(v.get('cwe_id', 'N/A'))} &nbsp;|&nbsp; <b>Confidence:</b> {conf}", body_style))
            story.append(Paragraph(f"<b>Description:</b> {desc}", body_style))
            story.append(Paragraph(f"<b>Impact:</b> {_t(v.get('impact', 'See severity and CVSS vector.'))}", body_style))
            story.append(Paragraph("<b>Evidence / Proof of Concept:</b>", body_style))
            story.append(Paragraph(poc, code_style))
            patch = v.get("remediation_patch") or v.get("remediation")
            if patch:
                story.append(Paragraph("<b>Remediation:</b>", body_style))
                story.append(Paragraph(_t(patch), code_style))
            story.append(Spacer(1, 8))

    # 5, 6, 7 tiers
    _add_tier("5. Confirmed Findings", confirmed)
    _add_tier("6. Probable Findings", probable)
    _add_tier("7. Unconfirmed Observations", unconfirmed)

    story.append(Paragraph("8. Evidence for Each Material Finding", h2_style))
    story.append(Paragraph("Each finding above includes reproduction PoC, endpoint, and confidence. Evidence is retained in sandbox spillway and Caido proxy logs.", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("9. Severity and Confidence", h2_style))
    story.append(Paragraph("Severity from CVSS 3.1 vector; confidence mirrors verification status (Confirmed=high, Probable=medium, Unconfirmed=low).", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("10. Impact", h2_style))
    story.append(Paragraph("Per-finding impact is listed above; where not explicit, severity is the primary risk indicator.", body_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("11. Remediation", h2_style))
    story.append(Paragraph(_t(recommendations) or "Apply parameterized queries, output encoding, least privilege, strict access controls, and patch management.", body_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("12. Limitations", h2_style))
    story.append(Paragraph(
        "Assessment is point-in-time, scope-limited, and tool-assisted. Coverage depends on target state, authentication, and rate limits. Findings require human review before remediation. "
        + INTEGRITY_STATEMENT_PDF, body_style))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
    story.append(Paragraph(f"<i>Integrity Statement:</i> {INTEGRITY_STATEMENT_PDF}", body_style))
    story.append(Paragraph("<i>Report generated by RakshakX Community Edition — Rudraksh AGI (GSTIN 24NKPM5455A1ZX).</i>", body_style))

    doc.build(story)
    logger.info("Generated PDF assessment report at %s", output_path)
    return output_path
