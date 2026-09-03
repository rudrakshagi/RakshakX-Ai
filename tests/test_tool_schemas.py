"""Tests that the agent tool-calling schemas are valid AND natural for LLMs.

Two concerns:
1. Schema quality: every tool the LLM sees must have a well-formed JSON object
   schema where each property carries a human-readable description.
2. Round-trip: tools must execute from a JSON-args invocation and return a JSON
   string (so the results are machine-parseable back into the agent loop).
"""

from __future__ import annotations

import json
from typing import Any

from rakshak.agents.factory import build_rakshak_agent
from tests.conftest import invoke_tool

# Tools that need no coordinator/mailbox and return deterministic results even
# with an empty context dict. These are exercised for round-trip proof.
_ROUNDTRIP_SAFE: dict[str, dict[str, Any]] = {
    "think": {"thought": "Probe the login form for credential stuffing."},
    "load_skill": {"skill_name": "sql_injection"},
    "create_todo": {"id": "probe_login", "task": "Fuzz /login for auth bypass"},
    "list_todos": {},
    "create_note": {"title": "endpoints", "content": "/api/users, /login, /admin"},
    "list_notes": {},
    "mark_todo_done": {"id": "probe_login"},
    "get_note": {"title": "endpoints"},
}


def _schema_of(tool: Any) -> dict[str, Any]:
    return tool.params_json_schema


def test_all_exposed_tools_have_valid_object_schema() -> None:
    agent = build_rakshak_agent(name="Root", is_root=True)
    assert agent.tools, "agent must expose tools"
    for tool in agent.tools:
        schema = _schema_of(tool)
        assert isinstance(schema, dict), f"{tool.name}: schema must be a dict"
        assert schema.get("type") == "object", f"{tool.name}: root type must be 'object'"
        assert isinstance(schema.get("properties"), dict), f"{tool.name}: must have properties"


def test_every_parameter_has_natural_description() -> None:
    agent = build_rakshak_agent(name="Root", is_root=True)
    for tool in agent.tools:
        props = _schema_of(tool).get("properties", {})
        for pname, pshape in props.items():
            if not isinstance(pshape, dict):
                continue
            desc = pshape.get("description")
            assert desc and desc.strip(), (
                f"{tool.name}.{pname} is missing a description; "
                "add Annotated[type, '...'] to the tool parameter."
            )
            assert len(desc.strip()) >= 8, (
                f"{tool.name}.{pname} has a too-short description: {desc!r}"
            )
            # Every property must declare a concrete type (or a resolved anyOf),
            # otherwise strict providers will reject the schema.
            assert any(
                k in pshape for k in ("type", "anyOf", "enum")
            ), f"{tool.name}.{pname} must declare a type/anyOf/enum"


def test_optional_and_defaulted_params_are_not_required() -> None:
    agent = build_rakshak_agent(name="Root", is_root=True)
    for tool in agent.tools:
        schema = _schema_of(tool)
        props = schema.get("properties", {})
        required = schema.get("required")
        if required is None:
            continue
        for name in required:
            prop = props.get(name)
            assert isinstance(prop, dict), f"{tool.name}.{name}: missing property in schema"
            assert "default" not in prop, f"{tool.name}.{name} has a default but is required"
            types = {t.get("type") for t in prop.get("anyOf", [])} if isinstance(prop.get("anyOf"), list) else {prop.get("type")}
            assert "null" not in types, f"{tool.name}.{name} is nullable but required"


def _valid_json(value: str) -> dict[str, Any]:
    return json.loads(value)


async def test_safe_tools_roundtrip_from_json_args() -> None:
    agent = build_rakshak_agent(name="Root", is_root=True)
    by_name = {tool.name: tool for tool in agent.tools}
    for name, kwargs in _ROUNDTRIP_SAFE.items():
        tool = by_name.get(name)
        assert tool is not None, f"missing tool {name} on agent"
        raw = await invoke_tool(tool, {}, **kwargs)
        assert isinstance(raw, str), f"{name}: tool must return a string"
        result = _valid_json(raw)
        assert isinstance(result, dict), f"{name}: result must be JSON object"


async def test_finish_scan_rejects_empty_sections_naturally() -> None:
    from rakshak.tools.finish.tool import finish_scan

    raw = await invoke_tool(
        finish_scan,
        {},
        executive_summary="",
        methodology="",
        technical_analysis="",
        recommendations="",
    )
    result = _valid_json(raw)
    assert result.get("success") is False
    assert "errors" in result  # friendly, structured validation feedback


async def test_create_vulnerability_report_cvss_validation() -> None:
    from rakshak.tools.reporting.tool import create_vulnerability_report

    raw = await invoke_tool(
        create_vulnerability_report,
        {},
        title="Reflected XSS",
        description="Classic reflected XSS in search param.",
        category="XSS",
        cwe_id="CWE-79",
        cvss_metrics={"attack_vector": "Z"},  # invalid -> should reject
        reproduction_steps=["curl -s 'http://t/?q=<script>alert(1)</script>'"],
        exploit_poc="<script>alert(1)</script>",
    )
    result = _valid_json(raw)
    assert result.get("success") is False
