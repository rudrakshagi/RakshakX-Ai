"""Unit tests for new agent-capability changes: skills, prompt, follow-up envelope.

No docker/network/LLM. Covers:
- 4 new vulnerability skills (file_upload, open_redirect_cors, ssti, lfi_path_traversal)
- root/specialist prompt directives (COVERAGE MATRIX, EXPAND ON HIT, autonomy, spill)
- _follow_up_directive category routing + success-envelope regression
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from rakshak.agents.prompt import render_system_prompt
from rakshak.benchmark.prompts import T01_PROMPT
from rakshak.tools.load_skill.tool import _list_all_skills, load_skill
from rakshak.tools.reporting.tool import _follow_up_directive, create_vulnerability_report
from tests.conftest import invoke_tool
from tests.test_tools_reporting import VALID_METRICS

NEW_SKILLS = ["file_upload", "open_redirect_cors", "ssti", "lfi_path_traversal"]

# Full 12-class coverage matrix expected in the root prompt.
MATRIX_SKILLS = [
    "sql_injection",
    "xss",
    "idor",
    "authentication_jwt",
    "ssrf",
    "rce",
    "race_conditions",
    "file_upload",
    "open_redirect_cors",
    "ssti",
    "lfi_path_traversal",
    "agent_browser",
]

SKILLS_DIR = Path("rakshak/skills/vulnerabilities")


# ---------------------------------------------------------------------------
# 1. Skills
# ---------------------------------------------------------------------------


def test_list_all_skills_includes_new_names():
    available = _list_all_skills()
    for name in NEW_SKILLS:
        assert name in available, f"new skill '{name}' missing from _list_all_skills()"


@pytest.mark.parametrize("skill", NEW_SKILLS)
def test_new_skill_file_content(skill):
    path = SKILLS_DIR / f"{skill}.md"
    assert path.exists(), f"missing playbook {path}"
    text = path.read_text(encoding="utf-8")
    assert "CWE" in text
    assert "CVSS" in text
    assert "Remediation" in text or "remediation" in text
    # A curl example or another tool command example.
    assert "curl" in text or "agent-browser" in text or "ffuf" in text or "sqlmap" in text


@pytest.mark.parametrize("skill", NEW_SKILLS)
def test_load_skill_tool_returns_playbook(skill):
    """Via the real load_skill FunctionTool (ToolContext stub in conftest)."""
    res = asyncio.run(invoke_tool(load_skill, {}, skill_name=skill))
    payload = json.loads(res)
    assert payload["success"] is True
    assert payload["playbook"].strip(), f"empty playbook for '{skill}'"
    # NOTE: the tool truncates long playbooks to ~1200 chars to save context
    # tokens (pre-existing behavior — all 12 skills truncate), so the tail
    # reporting section (CWE/CVSS/Remediation) is only asserted at file level
    # above. Here just check the head survived with the playbook title.
    assert "Offensive Playbook" in payload["playbook"]


def test_load_skill_unknown_lists_new_skills():
    res = asyncio.run(invoke_tool(load_skill, {}, skill_name="definitely_not_a_skill_xyz"))
    payload = json.loads(res)
    assert payload["success"] is False
    for name in NEW_SKILLS:
        assert name in payload["available_skills"]


# ---------------------------------------------------------------------------
# 2. Prompt
# ---------------------------------------------------------------------------


def test_root_prompt_capability_directives():
    prompt = render_system_prompt(is_root=True)
    assert "COVERAGE MATRIX" in prompt
    assert "EXPAND ON HIT" in prompt
    assert "YOUR JUDGMENT LEADS" in prompt
    assert "spill" in prompt
    for name in MATRIX_SKILLS:
        assert name in prompt, f"matrix skill '{name}' missing from root prompt"


def test_specialist_prompt_skill_guidance_no_finish():
    specialist = render_system_prompt(is_root=False)
    assert "load_skill" in specialist
    # Pre-existing behavior, consistent with tests/test_agents_prompt.py:
    assert "never call `finish_scan`" in specialist
    assert "finish_scan` —" not in specialist


def test_benchmark_t01_verbatim_block_untouched():
    prompt = render_system_prompt(is_root=True, scan_mode="T01")
    assert "BENCHMARK PROTOCOL" in prompt
    assert T01_PROMPT in prompt


# ---------------------------------------------------------------------------
# 3. Follow-up directive routing
# ---------------------------------------------------------------------------

# (category label, endpoint, expected skill marker in the directive)
FOLLOW_UP_CASES = [
    ("SQL Injection", "/api/users?id=1", "sql_injection"),
    ("XSS", "/search?q=x", "xss"),
    ("IDOR", "/api/orders/124", "idor"),
    ("JWT Authentication Bypass", "/api/auth/refresh", "authentication_jwt"),
    ("SSRF", "/fetch?url=x", "ssrf"),
    ("RCE", "/exec?cmd=id", "rce"),
    ("Race Condition", "/api/coupon/apply", "race_conditions"),
    ("Unrestricted File Upload", "/upload", "file_upload"),
    ("Open Redirect", "/login?next=x", "open_redirect_cors"),
    ("CORS Misconfiguration", "/api/me", "open_redirect_cors"),
    ("SSTI", "/profile?name=x", "ssti"),
    ("Path Traversal", "/download?file=x", "lfi_path_traversal"),
    ("LFI", "/page?file=x", "lfi_path_traversal"),
]


@pytest.mark.parametrize("category,endpoint,skill", FOLLOW_UP_CASES)
def test_follow_up_routes_to_skill(category, endpoint, skill):
    directive = _follow_up_directive(category, endpoint)
    assert skill in directive
    assert endpoint in directive  # endpoint appended when present


def test_follow_up_generic_fallback_unknown_category():
    directive = _follow_up_directive("Something Entirely Novel", "/some/endpoint")
    assert "sibling" in directive.lower()
    assert "/some/endpoint" in directive
    for skill in MATRIX_SKILLS:
        if skill == "agent_browser":
            continue
        assert f"Skill: {skill}." not in directive


@pytest.mark.parametrize("category", ["SQL Injection", "XSS", "Something Entirely Novel"])
def test_follow_up_no_endpoint_no_start_at(category):
    directive = _follow_up_directive(category, None)
    assert "Start at" not in directive


# ---------------------------------------------------------------------------
# 4. Success envelope regression
# ---------------------------------------------------------------------------


def test_success_envelope_includes_follow_up():
    """Mirror tests/test_tools_reporting.py invocation via invoke_tool."""
    res = asyncio.run(invoke_tool(
        create_vulnerability_report,
        {},
        title="SQLi in search",
        description="desc",
        category="SQL Injection",
        cwe_id="CWE-89",
        cvss_metrics=VALID_METRICS,
        reproduction_steps=["step"],
        exploit_poc="curl",
        affected_endpoint="/api/users?id=1",
    ))
    payload = json.loads(res)
    assert payload["success"] is True
    for key in ("success", "title", "severity", "follow_up"):
        assert key in payload, f"envelope missing '{key}'"
    assert "sql_injection" in payload["follow_up"]
    assert "/api/users?id=1" in payload["follow_up"]


def test_success_envelope_no_endpoint_no_start_at():
    res = asyncio.run(invoke_tool(
        create_vulnerability_report,
        {},
        title="Stored XSS",
        description="desc",
        category="XSS",
        cwe_id="CWE-79",
        cvss_metrics=VALID_METRICS,
        reproduction_steps=["step"],
        exploit_poc="curl",
    ))
    payload = json.loads(res)
    assert payload["success"] is True
    assert "follow_up" in payload
    assert "xss" in payload["follow_up"]
    assert "Start at" not in payload["follow_up"]
