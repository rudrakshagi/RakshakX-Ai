"""Unit tests for agent factory tool assembly."""

from __future__ import annotations

from rakshak.agents.factory import build_rakshak_agent, make_child_factory
from rakshak.agents.prompt import render_system_prompt


def test_build_root_agent_has_lifecycle():
    agent = build_rakshak_agent(name="Root", is_root=True)
    names = {t.name for t in agent.tools}
    assert "finish_scan" in names
    assert "agent_finish" not in names


def test_build_child_agent_has_agent_finish():
    agent = build_rakshak_agent(name="Child", is_root=False)
    names = {t.name for t in agent.tools}
    assert "agent_finish" in names
    assert "finish_scan" not in names


def test_child_factory_builds_children():
    factory = make_child_factory(scan_mode="quick", is_whitebox=True)
    agent = factory(name="SQLi", skills=["sql_injection"])
    assert agent.name == "SQLi"
    assert "sql_injection" in render_system_prompt(skills=["sql_injection"])


def test_build_root_instruction_deduplicated():
    agent = build_rakshak_agent(name="Root", is_root=True)
    # instructions should be empty now (dedup), all content in base_instructions
    assert agent.instructions == ""


def test_tools_have_no_duplicate_think():
    agent = build_rakshak_agent(name="Root", is_root=True)
    names = [t.name for t in agent.tools]
    assert names.count("think") == 1
