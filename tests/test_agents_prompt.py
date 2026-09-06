"""Unit tests for system prompt rendering."""

from __future__ import annotations

from rakshak.agents.prompt import render_system_prompt


def test_root_role():
    prompt = render_system_prompt(is_root=True)
    assert "ROOT ORCHESTRATOR" in prompt
    assert "finish_scan" in prompt


def test_child_role():
    prompt = render_system_prompt(is_root=False)
    assert "SPECIALIST SUBAGENT" in prompt
    assert "agent_finish" in prompt


def test_scan_mode_and_whitebox():
    prompt = render_system_prompt(is_root=True, scan_mode="quick", is_whitebox=True)
    assert "QUICK" in prompt
    assert "WHITEBOX" in prompt


def test_blackbox_default():
    prompt = render_system_prompt(is_root=True)
    assert "BLACKBOX" in prompt


def test_skills_listed():
    prompt = render_system_prompt(is_root=True, skills=["sql_injection", "xss"])
    assert "sql_injection" in prompt
    assert "xss" in prompt


def test_authorization_framing_reduces_refusal():
    prompt = render_system_prompt(is_root=True)
    assert "explicit authorization" in prompt
    assert "do not refuse" in prompt


def test_shell_never_boolean_contract():
    for root in (True, False):
        prompt = render_system_prompt(is_root=root)
        assert "NEVER send `shell` as true/false" in prompt
        assert '"cmd"' in prompt


def test_verification_taxonomy():
    prompt = render_system_prompt(is_root=True)
    assert "Confirmed" in prompt
    assert "Probable" in prompt
    assert "Unconfirmed" in prompt


def test_root_child_separation():
    root = render_system_prompt(is_root=True)
    child = render_system_prompt(is_root=False)
    assert "create_agent" in root
    assert "wait_for_agents" in root
    assert "executive_summary" in root
    assert "never call `finish_scan`" in child
    assert "agent_finish" in child
    # child must not be told to orchestrate / finish the scan
    assert "finish_scan` —" not in child


def test_load_skill_guidance():
    for root in (True, False):
        assert "load_skill" in render_system_prompt(is_root=root)


def test_compact_line_budget():
    for root in (True, False):
        lines = len(render_system_prompt(is_root=root).splitlines())
        assert 45 <= lines <= 85, f"rendered {lines} lines, expected compact 45-85"
