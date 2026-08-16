"""Scan finalization tool for root orchestrators."""

from __future__ import annotations

import json
import logging
from agents import RunContextWrapper, function_tool

logger = logging.getLogger(__name__)


@function_tool(timeout=60)
async def finish_scan(
    ctx: RunContextWrapper,
    executive_summary: str,
    methodology: str,
    technical_analysis: str,
    recommendations: str,
) -> str:
    """Finalize the security assessment and persist customer-facing reports.
    
    ROOT AGENTS ONLY. Validates that all narrative sections are populated,
    finalizes findings in the report state, and signals scan completion.
    """
    inner = ctx.context if isinstance(ctx.context, dict) else {}
    parent_id = inner.get("parent_id")

    if parent_id is not None:
        return json.dumps({
            "success": False,
            "error": "finish_scan can only be called by the Root Orchestrator. Subagents must call agent_finish.",
        })

    errors = []
    if not executive_summary.strip():
        errors.append("Executive summary cannot be empty")
    if not methodology.strip():
        errors.append("Methodology cannot be empty")
    if not technical_analysis.strip():
        errors.append("Technical analysis cannot be empty")
    if not recommendations.strip():
        errors.append("Recommendations cannot be empty")

    if errors:
        return json.dumps({"success": False, "error": "Validation failed", "errors": errors})

    from rakshak.report.state import get_global_report_state
    report_state = get_global_report_state()
    vuln_count = 0
    if report_state is not None:
        report_state.update_final_narrative(
            executive_summary=executive_summary.strip(),
            methodology=methodology.strip(),
            technical_analysis=technical_analysis.strip(),
            recommendations=recommendations.strip(),
        )
        vuln_count = len(report_state.vulnerabilities)

    logger.info("finish_scan: scan finalized with %d confirmed vulnerabilities", vuln_count)
    return json.dumps({
        "success": True,
        "scan_completed": True,
        "total_vulnerabilities": vuln_count,
        "message": "Scan finalized successfully. Executive reports written.",
    })
