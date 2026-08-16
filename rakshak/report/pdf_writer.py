"""Executive PDF report generation using ReportLab."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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

    # Findings Summary Metric Cards
    crit = sum(1 for v in vulnerabilities if v.get("severity") == "critical")
    high = sum(1 for v in vulnerabilities if v.get("severity") == "high")
    med = sum(1 for v in vulnerabilities if v.get("severity") == "medium")
    low = sum(1 for v in vulnerabilities if v.get("severity") == "low")

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

    # Executive Summary Section
    story.append(Paragraph("1. Executive Summary", h2_style))
    story.append(Paragraph(executive_summary or "Autonomous security assessment completed with dynamic verification.", body_style))
    story.append(Spacer(1, 10))

    # Methodology Section
    story.append(Paragraph("2. Assessment Methodology", h2_style))
    story.append(Paragraph(methodology or "Conducted dynamic multi-agent probing inside an isolated Kali Linux sandbox.", body_style))
    story.append(Spacer(1, 10))

    # Technical Analysis
    story.append(Paragraph("3. Technical Analysis", h2_style))
    story.append(Paragraph(technical_analysis or "Target endpoints were mapped, probed, and exploited programmatically.", body_style))
    story.append(Spacer(1, 15))

    # Verified Findings
    story.append(Paragraph("4. Confirmed Vulnerability Findings", h2_style))
    if not vulnerabilities:
        story.append(Paragraph("<i>No confirmed vulnerabilities were identified during this assessment.</i>", body_style))
    else:
        for idx, v in enumerate(vulnerabilities, start=1):
            title = v.get("title", "Untitled Vulnerability")
            sev = v.get("severity", "medium").upper()
            score = v.get("cvss_score", "N/A")
            ep = v.get("endpoint", "N/A")
            desc = v.get("description", "No description provided.")
            poc = v.get("poc", "# No PoC provided")

            story.append(Paragraph(f"<b>{idx}. {title}</b> — <font color='#b91c1c'><b>{sev} (CVSS {score})</b></font>", h2_style))
            story.append(Paragraph(f"<b>Affected Target:</b> <code>{ep}</code> &nbsp;|&nbsp; <b>CWE:</b> {v.get('cwe_id', 'N/A')}", body_style))
            story.append(Paragraph(f"<b>Description:</b> {desc}", body_style))
            story.append(Paragraph("<b>Proof of Concept Command / Script:</b>", body_style))
            story.append(Paragraph(poc.replace("<", "&lt;").replace(">", "&gt;"), code_style))

            patch = v.get("remediation_patch")
            if patch:
                story.append(Paragraph("<b>Remediation Guidance:</b>", body_style))
                story.append(Paragraph(patch.replace("<", "&lt;").replace(">", "&gt;"), code_style))
            story.append(Spacer(1, 10))

    # Recommendations Section
    story.append(Paragraph("5. Strategic Recommendations", h2_style))
    story.append(Paragraph(recommendations or "Implement secure input sanitization, parameterized queries, and strict access controls.", body_style))

    doc.build(story)
    logger.info("Generated PDF assessment report at %s", output_path)
    return output_path
