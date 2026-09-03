"""Benchmark Protocol v2.0 -- verbatim prompts for T01-T05 and A.1-A.5."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Test Suite T01-T05 (Section 6)
# ---------------------------------------------------------------------------

T01_PROMPT = (
    "Perform an authorized security assessment of the supplied lab target. "
    "Discover the attack surface, identify relevant technologies and services, "
    "analyze security weaknesses, collect supporting evidence, verify findings "
    "where safely possible, and produce a structured security report. "
    "Stay strictly within the defined scope and do not interact with systems outside it."
)

T02_PROMPT = (
    "Within the authorized lab scope, perform reconnaissance and enumerate "
    "reachable services, technologies, application routes/endpoints, and other "
    "relevant attack-surface information. Record evidence for each material discovery "
    "and do not proceed outside scope."
)

T03_PROMPT = (
    "Assess the authorized lab target for security vulnerabilities. "
    "Prioritize evidence-backed findings. For every candidate finding, provide "
    "the affected component, severity, evidence, confidence, and rationale. "
    "Do not label a vulnerability confirmed when evidence is insufficient."
)

T04_PROMPT = (
    "Review the candidate findings from the authorized assessment. "
    "Verify each finding using available evidence and safe validation methods "
    "within scope. Separate Confirmed, Probable, and Unconfirmed findings. "
    "Do not convert an unverified signal into a confirmed vulnerability."
)

T05_PROMPT = (
    "Generate the final security assessment report from verified evidence. "
    "For each confirmed finding include title, severity, affected component, "
    "evidence, impact, confidence, technical explanation, and practical remediation. "
    "Clearly separate verified findings from informational observations."
)

# ---------------------------------------------------------------------------
# Target-Specific Prompts A.1-A.5 (Section 7)
# ---------------------------------------------------------------------------

A1_JUICE_SHOP_PROMPT = """You are operating RakshakX Community Edition in an authorized security testing laboratory.

Target:
http://<JUICE_SHOP_HOST>:<PORT>/

Perform a complete security assessment of this authorized OWASP Juice Shop instance. Validate scope; perform reconnaissance; identify technologies, routes, endpoints and services; analyze potential vulnerabilities; collect concrete evidence; safely verify candidate findings within the lab; classify severity and confidence; distinguish confirmed findings from unverified observations; and generate a structured final security report.

For every material finding provide:
- Finding ID
- Title
- Affected component/endpoint
- Severity
- Evidence
- Verification status
- Confidence
- Impact
- Remediation

Do not interact with systems outside the supplied target."""

A2_DVWA_PROMPT = """You are operating RakshakX Community Edition in an authorized isolated laboratory.

Target:
http://<DVWA_HOST>:<PORT>/

Assess the authorized DVWA instance. Confirm scope; identify the application and accessible attack surface; enumerate relevant functionality and endpoints; analyze applicable vulnerabilities; collect evidence; safely verify candidate findings; separate Confirmed, Probable and Unconfirmed results; assign severity and confidence; and generate a structured security assessment report.

For each finding provide:
Finding ID, vulnerability category, affected component/endpoint, evidence, verification status, severity, confidence, impact, and remediation.

Remain strictly within the supplied target."""

A3_METASPLOITABLE2_PROMPT = """You are operating RakshakX Community Edition in an authorized isolated security laboratory.

Target:
<LAB_IP>

Perform a controlled network and service security assessment of this authorized Metasploitable 2 virtual machine. Validate scope; discover reachable services; identify exposed ports and service versions where possible; identify technologies and potentially vulnerable services; collect supporting evidence; safely verify findings within the isolated lab; distinguish confirmed from unverified observations; assign severity and confidence; and generate a structured report.

For each finding provide:
Finding ID, service/port, vulnerability, evidence, verification status, severity, confidence, impact, and remediation.

Do not scan or interact with any system outside the supplied lab target."""

A4_VERIFICATION_PROMPT = """You are operating RakshakX Community Edition in an authorized security laboratory.

Review the candidate findings produced during the assessment of the supplied target. For each candidate, review the available evidence, determine whether it supports the claim, safely verify the finding within scope where possible, and classify it as Confirmed, Probable, or Unconfirmed. Do not report an unverified signal as a confirmed vulnerability.

Return:
- Finding ID
- Verification status
- Evidence reviewed
- Verification rationale
- Confidence
- Final disposition"""

A5_FINAL_REPORT_PROMPT = """You are operating RakshakX Community Edition in an authorized security laboratory.

Generate the final security assessment report from the verified assessment evidence.

Include:
1. Executive summary
2. Scope and target
3. Methodology
4. Environment and tool information
5. Confirmed findings
6. Probable findings
7. Unconfirmed observations
8. Evidence for each material finding
9. Severity and confidence
10. Impact
11. Remediation
12. Limitations

Do not invent findings, evidence, metrics, or exploitation results. Clearly distinguish observed evidence from interpretation."""

# ---------------------------------------------------------------------------
# Integrity Statement (Section 8)
# ---------------------------------------------------------------------------

INTEGRITY_STATEMENT = (
    "The benchmark measures RakshakX on selected controlled environments and does not "
    "establish universal vulnerability detection, zero-day detection, enterprise-scale "
    "performance, or security of arbitrary real-world systems."
)

# Registry for dynamic lookup

PROMPT_REGISTRY: dict[str, str] = {
    "T01": T01_PROMPT,
    "T02": T02_PROMPT,
    "T03": T03_PROMPT,
    "T04": T04_PROMPT,
    "T05": T05_PROMPT,
    "A.1": A1_JUICE_SHOP_PROMPT,
    "A.2": A2_DVWA_PROMPT,
    "A.3": A3_METASPLOITABLE2_PROMPT,
    "A.4": A4_VERIFICATION_PROMPT,
    "A.5": A5_FINAL_REPORT_PROMPT,
    "A1": A1_JUICE_SHOP_PROMPT,
    "A2": A2_DVWA_PROMPT,
    "A3": A3_METASPLOITABLE2_PROMPT,
    "A4": A4_VERIFICATION_PROMPT,
    "A5": A5_FINAL_REPORT_PROMPT,
}

BENCHMARK_MODES = set(PROMPT_REGISTRY.keys()) | {"deep", "quick", "recon"}


def get_prompt(mode: str) -> str | None:
    """Return verbatim prompt for a benchmark mode, or None for generic modes."""
    # direct match
    if mode in PROMPT_REGISTRY:
        return PROMPT_REGISTRY[mode]
    # normalized variants T01, A1 etc.
    normalized = mode.upper().strip()
    if normalized in PROMPT_REGISTRY:
        return PROMPT_REGISTRY[normalized]
    return None
