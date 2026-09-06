"""Factory for building Root and Child SandboxAgents with configured tools."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from agents.agent import ToolsToFinalOutputResult
from agents.sandbox import SandboxAgent
from agents.sandbox.capabilities import Shell
from agents.tool import Tool

from rakshak.agents.prompt import render_system_prompt
from rakshak.tools.agents_graph.tools import (
    agent_finish,
    create_agent,
    send_message_to_agent,
    view_agent_graph,
    wait_for_agents,
)
from rakshak.tools.finish.tool import finish_scan
from rakshak.tools.load_skill.tool import load_skill
from rakshak.tools.notes.tools import create_note, get_note, list_notes
from rakshak.tools.proxy.tools import list_requests, view_request
from rakshak.tools.reporting.tool import create_vulnerability_report
from rakshak.tools.thinking.tool import think
from rakshak.tools.todo.tools import create_todo, list_todos, mark_todo_done

logger = logging.getLogger(__name__)


def _is_optional_prop(prop: Any) -> bool:
    """A property is optional if it has a default or is explicitly nullable."""
    if isinstance(prop, dict):
        if "default" in prop:
            return True
        any_of = prop.get("anyOf")
        if isinstance(any_of, list):
            return any(t.get("type") == "null" for t in any_of if isinstance(t, dict))
        if prop.get("type") == "null":
            return True
    return False


def _normalize_tool_schema(tool: Tool) -> Tool:
    """Make generated JSON schemas well-formed and natural for LLMs.

    - Ensures a JSON object root with ``properties`` and ``additionalProperties: false``
      (required by strict providers such as Groq).
    - Recomputes ``required`` so only parameters without a default or without a nullable
      type are required — the SDK otherwise marks every parameter as required, which
      produces unnatural schemas for optional arguments like ``first`` or ``skills``.
    """
    schema = getattr(tool, "params_json_schema", None)
    if not isinstance(schema, dict):
        return tool
    schema.setdefault("type", "object")
    schema["additionalProperties"] = False
    props = schema.get("properties")
    if not isinstance(props, dict) or not props:
        schema.pop("required", None)
        return tool
    required = schema.get("required")
    if isinstance(required, list):
        filtered = [name for name in required if not _is_optional_prop(props.get(name))]
        if filtered:
            schema["required"] = filtered
        else:
            schema.pop("required", None)
    return tool


def _normalize_tools(tools: list[Tool]) -> list[Tool]:
    return [_normalize_tool_schema(t) for t in tools]


_BASE_TOOLS: tuple[Tool, ...] = (
    think,
    load_skill,
    create_todo,
    list_todos,
    mark_todo_done,
    create_note,
    list_notes,
    get_note,
    list_requests,
    view_request,
    create_vulnerability_report,
    view_agent_graph,
    send_message_to_agent,
    wait_for_agents,
    create_agent,
)


def _finish_tool_use_behavior(ctx: Any, tool_results: list[Any]) -> ToolsToFinalOutputResult:
    """Evaluate whether a lifecycle tool (`finish_scan` or `agent_finish`) was called to stop the turn."""
    for tr in tool_results:
        tool_name = getattr(tr.tool, "name", "")
        if tool_name in ("finish_scan", "agent_finish"):
            return ToolsToFinalOutputResult(is_final_output=True, final_output=tr.output)
    return ToolsToFinalOutputResult(is_final_output=False, final_output=None)


_EXEC_COMMAND_CONTRACT = (
    "Runs a command in a PTY, returning output or a session ID for ongoing interaction. "
    'Arguments JSON shape: {"cmd": "<shell command string, REQUIRED>", '
    '"workdir": "<optional directory, defaults to turn cwd>", "tty": false, '
    '"shell": "<optional shell binary path as a STRING, e.g. \\"/bin/bash\\"; '
    'OMIT this field unless you need a specific binary>"}. '
    "IMPORTANT: `shell` must be a string path or omitted entirely — NEVER send a boolean "
    "(sending `true`/`false` fails validation and kills the turn). "
    'Example: {"cmd": "curl -sI https://example.com/", "workdir": "/workspace", "tty": false}.'
)

_SHELL_PROP_CONTRACT = (
    "Optional shell binary path as a STRING (e.g. \"/bin/bash\"). "
    "Omit this field to use the default shell. NEVER send true/false."
)


def _configure_shell_tools(toolset: Any) -> None:
    """Harden the SDK Shell capability tools against the observed `shell: true` failure.

    During the rudra-passive live run the model repeatedly sent a boolean `shell`
    flag to `exec_command`, but the SDK schema requires a string-or-omitted value.
    Every attempt raised a pydantic ValidationError and killed the turn in a loop.
    This configurator (wired via ``Shell(configure_tools=...)``) does two things:

    1. Rewrites the tool + `shell`-property descriptions with an exact JSON
       contract, example, and an explicit never-boolean warning.
    2. Wraps ``on_invoke_tool`` with a defensive coercion that drops a boolean
       ``shell`` key before the SDK validator sees it, so one confused model
       call degrades to a default-shell run instead of a turn failure.
    """
    exec_tool = getattr(toolset, "exec_command", None)
    if exec_tool is None:
        return
    try:
        exec_tool.description = _EXEC_COMMAND_CONTRACT
        schema = getattr(exec_tool, "params_json_schema", None)
        if isinstance(schema, dict):
            props = schema.get("properties")
            if isinstance(props, dict) and isinstance(props.get("shell"), dict):
                props["shell"]["description"] = _SHELL_PROP_CONTRACT
    except Exception:
        logger.warning("Failed to patch exec_command tool contract", exc_info=True)

    original = getattr(exec_tool, "on_invoke_tool", None)
    if not callable(original) or getattr(original, "_rakshak_shell_coerced", False):
        return

    async def _invoke_coerced(ctx: Any, raw: str) -> Any:
        try:
            data = json.loads(raw)
        except Exception:
            return await original(ctx, raw)
        if isinstance(data, dict):
            sh = data.get("shell")
            if isinstance(sh, bool) or (isinstance(sh, str) and sh.lower() in ("true", "false")):
                logger.warning("Dropping boolean shell flag %r from exec_command args (model mistake)", sh)
                data.pop("shell", None)
                raw = json.dumps(data)
        return await original(ctx, raw)

    _invoke_coerced._rakshak_shell_coerced = True  # type: ignore[attr-defined]
    try:
        exec_tool.on_invoke_tool = _invoke_coerced
    except Exception:
        logger.warning("Failed to wrap exec_command invoker", exc_info=True)


def build_rakshak_agent(
    *,
    name: str = "Root Agent",
    skills: list[str] | None = None,
    is_root: bool = True,
    scan_mode: str = "deep",
    is_whitebox: bool = False,
    extra_tools: Sequence[Tool] | None = None,
) -> SandboxAgent[Any]:
    """Construct an addressable SandboxAgent equipped with offensive tools and sandbox access."""
    base_instructions = render_system_prompt(
        skills=skills,
        is_root=is_root,
        scan_mode=scan_mode,
        is_whitebox=is_whitebox,
    )

    lifecycle_tool = finish_scan if is_root else agent_finish
    tools: list[Tool] = _normalize_tools([*_BASE_TOOLS, *(extra_tools or []), lifecycle_tool])

    logger.info(
        "Built %s agent '%s' (tools=%d, skills=%d, whitebox=%s)",
        "root" if is_root else "child",
        name,
        len(tools),
        len(skills or []),
        is_whitebox,
    )

    return SandboxAgent(
        name=name,
        base_instructions=base_instructions,
        instructions="",
        tools=tools,
        tool_use_behavior=_finish_tool_use_behavior,
        capabilities=[Shell(configure_tools=_configure_shell_tools)],
    )


def make_child_factory(
    *,
    scan_mode: str = "deep",
    is_whitebox: bool = False,
) -> Any:
    """Return a closure factory for spawning specialized child subagents."""
    def _factory(*, name: str, skills: list[str]) -> SandboxAgent[Any]:
        return build_rakshak_agent(
            name=name,
            skills=skills,
            is_root=False,
            scan_mode=scan_mode,
            is_whitebox=is_whitebox,
        )

    return _factory
