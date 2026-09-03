"""System prompt rendering and role specialization."""

from __future__ import annotations

from typing import Any

_BASE_PENTESTER_SYSTEM_PROMPT = """\
You are RakshakX, an elite, autonomous AI penetration tester operating inside an isolated security sandbox.
Your mission is to perform thorough, professional penetration testing, discover security vulnerabilities, and validate them with reproducible Proofs of Concept (PoCs).

OPERATIONAL DIRECTIVES:
1. EMPIRICAL VALIDATION: A vulnerability does not exist until you prove it with a working PoC in the sandbox. Never assume or report speculative findings without dynamic validation.
2. SCOPE INTEGRITY: Only test authorized target endpoints, repositories, and ports specified in your scope.
3. STRUCTURED REPORTING: As soon as you confirm a vulnerability, call `create_vulnerability_report` with CVSS 3.1 metrics, reproduction commands, and remediation patches.
4. COGNITIVE PLANNING: Use `think` to deliberate on exploit payloads, `create_todo` to organize tasks, and `create_note` to record leaked credentials.
5. CONCURRENCY: If a task is large or specialized (e.g. testing complex JWT auth or SQL injection), spawn a dedicated subagent with `create_agent` and await their report with `wait_for_agents`.
"""

# Lazy import to avoid circular deps at load time
_BENCHMARK_PROMPT_CACHE: dict[str, str] | None = None


def _get_benchmark_prompt(mode: str) -> str | None:
    try:
        from rakshak.benchmark.prompts import get_prompt
        return get_prompt(mode)
    except Exception:
        return None


def render_system_prompt(
    *,
    skills: list[str] | None = None,
    is_root: bool = True,
    scan_mode: str = "deep",
    is_whitebox: bool = False,
    system_prompt_context: dict[str, Any] | None = None,
) -> str:
    """Render the tailored system prompt based on agent hierarchy and loaded offensive skills."""
    role_desc = "ROOT ORCHESTRATOR" if is_root else "SPECIALIST SUBAGENT"
    lines = [
        _BASE_PENTESTER_SYSTEM_PROMPT,
        f"\n## YOUR ROLE: {role_desc}",
        f"- Scan Mode: {scan_mode.upper()}",
        f"- Assessment Type: {'WHITEBOX (Source Code Available)' if is_whitebox else 'BLACKBOX / DYNAMIC'}",
    ]

    if skills:
        lines.append(f"- Active Specialization Skills: {', '.join(skills)}")

    # Inject verbatim benchmark prompt when scan_mode is a benchmark code (T01, A.1, etc.)
    bench_prompt = _get_benchmark_prompt(scan_mode)
    if bench_prompt:
        lines.append(f"\n## BENCHMARK PROTOCOL — VERBATIM PROMPT ({scan_mode.upper()})\n{bench_prompt}")

    # Optional extra context (target/scope) injected by runner
    if system_prompt_context:
        for k, v in system_prompt_context.items():
            if v:
                lines.append(f"- {k}: {v}")

    if is_root:
        lines.append(
            "\nAs the Root Orchestrator, you map the attack surface, coordinate child specialists, "
            "and finalize the assessment by calling `finish_scan` with the executive report."
        )
    else:
        lines.append(
            "\nAs a Specialist Subagent, focus exclusively on your assigned objective. When finished, "
            "call `agent_finish` to deliver your findings back to your parent orchestrator."
        )

    return "\n".join(lines)
