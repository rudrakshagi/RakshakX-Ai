"""Factory for building Root and Child SandboxAgents with configured tools."""

from __future__ import annotations

import logging
from typing import Any, Sequence
from agents.agent import ToolsToFinalOutputResult
from agents.sandbox import SandboxAgent
from agents.sandbox.capabilities import Filesystem, Shell
from agents.tool import FunctionTool, Tool

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
    instructions = render_system_prompt(
        skills=skills,
        is_root=is_root,
        scan_mode=scan_mode,
        is_whitebox=is_whitebox,
    )

    lifecycle_tool = finish_scan if is_root else agent_finish
    tools: list[Tool] = [*_BASE_TOOLS, *(extra_tools or []), lifecycle_tool]

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
        instructions=instructions,
        tools=tools,
        tool_use_behavior=_finish_tool_use_behavior,
        capabilities=[Filesystem(), Shell()],
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
