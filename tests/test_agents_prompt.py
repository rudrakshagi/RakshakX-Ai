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
