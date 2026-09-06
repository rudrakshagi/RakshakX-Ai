"""Regression tests for the exec_command shell-contract hardening.

During the rudra-passive live run the model repeatedly sent ``{"shell": true}``
to the SDK's ``exec_command`` tool, whose schema requires a string-or-omitted
value. Every attempt raised a pydantic ValidationError and killed the turn in
a loop. ``_configure_shell_tools`` (wired via ``Shell(configure_tools=...)``)
patches the tool description and coerces boolean flags away.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from rakshak.agents.factory import _configure_shell_tools


def _stub_toolset() -> tuple[SimpleNamespace, list[str]]:
    """Return (toolset, seen) where seen records raw payloads reaching the original invoker."""
    seen: list[str] = []

    async def _original(ctx: Any, raw: str) -> str:
        seen.append(raw)
        return raw

    tool = SimpleNamespace(
        description="Runs a command in a PTY.",
        params_json_schema={
            "type": "object",
            "properties": {
                "cmd": {"type": "string"},
                "shell": {"type": "string", "description": "Shell binary to launch."},
            },
        },
        on_invoke_tool=_original,
    )
    return SimpleNamespace(exec_command=tool), seen


async def _invoke(toolset: SimpleNamespace, payload: str) -> str:
    return await toolset.exec_command.on_invoke_tool({}, payload)


async def test_contract_description_patched() -> None:
    toolset, _ = _stub_toolset()
    _configure_shell_tools(toolset)
    tool = toolset.exec_command
    assert "NEVER send a boolean" in tool.description
    assert '"cmd":' in tool.description  # exact JSON shape + example present
    shell_desc = tool.params_json_schema["properties"]["shell"]["description"]
    assert "NEVER send true/false" in shell_desc


async def test_boolean_shell_flag_dropped() -> None:
    toolset, seen = _stub_toolset()
    _configure_shell_tools(toolset)
    await _invoke(toolset, json.dumps({"cmd": "curl -sI https://example.com/", "shell": True}))
    assert len(seen) == 1
    assert "shell" not in json.loads(seen[0])


async def test_string_boolean_shell_flag_dropped() -> None:
    toolset, seen = _stub_toolset()
    _configure_shell_tools(toolset)
    for val in ("true", "false", "True", "False"):
        seen.clear()
        await _invoke(toolset, json.dumps({"cmd": "ls", "shell": val}))
        assert len(seen) == 1
        assert "shell" not in json.loads(seen[0])


async def test_string_shell_preserved() -> None:
    toolset, seen = _stub_toolset()
    _configure_shell_tools(toolset)
    await _invoke(toolset, json.dumps({"cmd": "id", "shell": "/bin/bash"}))
    assert json.loads(seen[0])["shell"] == "/bin/bash"


async def test_non_json_passthrough() -> None:
    toolset, seen = _stub_toolset()
    _configure_shell_tools(toolset)
    await _invoke(toolset, "not-json{{{")
    assert seen == ["not-json{{{"]


async def test_double_configure_does_not_double_wrap() -> None:
    toolset, seen = _stub_toolset()
    _configure_shell_tools(toolset)
    first_wrapper = toolset.exec_command.on_invoke_tool
    _configure_shell_tools(toolset)
    assert toolset.exec_command.on_invoke_tool is first_wrapper
    await _invoke(toolset, json.dumps({"cmd": "id", "shell": True}))
    assert "shell" not in json.loads(seen[0])


async def test_missing_exec_command_is_noop() -> None:
    _configure_shell_tools(SimpleNamespace())  # must not raise
    _configure_shell_tools(None)  # must not raise
