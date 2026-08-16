"""Multi-agent coordination tools backed by AgentCoordinator."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from agents import RunContextWrapper, function_tool
from rakshak.core.agents import coordinator_from_context

logger = logging.getLogger(__name__)


def _ctx(ctx: RunContextWrapper) -> dict[str, Any]:
    return ctx.context if isinstance(ctx.context, dict) else {}


def _render_completion_report(
    *,
    agent_name: str,
    agent_id: str,
    task: str,
    success: bool,
    result_summary: str,
    findings: list[str],
    recommendations: list[str],
) -> str:
    """Format a subagent completion report for deposition into the parent's inbox."""
    status_str = "SUCCESS" if success else "FAILED"
    lines = [
        f"== Subagent Completion Report: {agent_name} ({agent_id}) ==",
        f"Status: {status_str}",
        f"Timestamp: {datetime.now(UTC).isoformat()}",
    ]
    if task:
        lines.append(f"Assigned Task: {task}")
    lines.append("\nSummary of Findings & Work Completed:")
    lines.append(result_summary or "(no summary provided)")

    if findings:
        lines.append("\nKey Findings Observed:")
        lines.extend(f"- {f}" for f in findings)
    if recommendations:
        lines.append("\nRecommendations for Next Steps:")
        lines.extend(f"- {r}" for r in recommendations)

    return "\n".join(lines)


@function_tool(timeout=30)
async def view_agent_graph(ctx: RunContextWrapper) -> str:
    """Print the live multi-agent tree — all running, waiting, and completed agents."""
    inner = _ctx(ctx)
    coordinator = coordinator_from_context(inner)
    me = inner.get("agent_id")
    if coordinator is None:
        return json.dumps({"success": False, "error": "Coordinator missing in context"})

    parent_of, statuses, names, _ = await coordinator.graph_snapshot()
    lines: list[str] = []

    def _render_node(aid: str, depth: int) -> None:
        status = statuses.get(aid, "unknown")
        marker = "  <- YOU" if aid == me else ""
        lines.append(f"{'  ' * depth}- {names.get(aid, aid)} ({aid}) [{status}]{marker}")
        for child, p in parent_of.items():
            if p == aid:
                _render_node(child, depth + 1)

    roots = [aid for aid, parent in parent_of.items() if parent is None]
    for r in roots:
        _render_node(r, 0)

    return json.dumps({
        "success": True,
        "graph_tree": "\n".join(lines) or "(no agents registered)",
        "total_agents": len(parent_of),
    })


@function_tool(timeout=30)
async def send_message_to_agent(
    ctx: RunContextWrapper,
    target_agent_id: str,
    message: str,
    message_type: Literal["query", "instruction", "information"] = "information",
    priority: Literal["low", "normal", "high", "urgent"] = "normal",
) -> str:
    """Send an asynchronous message to another agent's mailbox."""
    inner = _ctx(ctx)
    coordinator = coordinator_from_context(inner)
    me = inner.get("agent_id")

    if coordinator is None or me is None:
        return json.dumps({"success": False, "error": "Missing agent context"})

    if target_agent_id == me:
        return json.dumps({"success": False, "error": "Cannot send message to yourself; use think() instead"})

    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    delivered = await coordinator.send(
        target_agent_id,
        {
            "id": msg_id,
            "from": me,
            "content": message,
            "type": message_type,
            "priority": priority,
        },
    )
    if not delivered:
        return json.dumps({"success": False, "error": f"Target agent '{target_agent_id}' not found"})

    return json.dumps({
        "success": True,
        "message_id": msg_id,
        "target": target_agent_id,
        "status": "delivered_to_mailbox",
    })


@function_tool(timeout=300)
async def wait_for_agents(
    ctx: RunContextWrapper,
    reason: str = "Waiting for child agents to complete their assigned tasks",
    timeout_seconds: int = 180,
) -> str:
    """Pause execution until a child agent finishes or sends a mailbox message."""
    inner = _ctx(ctx)
    coordinator = coordinator_from_context(inner)
    me = inner.get("agent_id")

    if coordinator is None or me is None:
        return json.dumps({"success": False, "error": "Missing agent coordinator context"})

    # Check if we already have pending messages waiting
    pending, items = await coordinator.consume_pending(me, include_items=True)
    if pending > 0:
        await coordinator.mark_running(me)
        return json.dumps({"success": True, "status": "message_arrived", "new_messages": pending})

    await coordinator.park_waiting(me, wait_kind="agents")
    try:
        arrived = await coordinator.wait_for_message(me, timeout=float(timeout_seconds))
        if not arrived:
            await coordinator.mark_running(me)
            return json.dumps({"success": True, "status": "timeout", "waited_seconds": timeout_seconds})
    except Exception:
        pass

    pending, _ = await coordinator.consume_pending(me, include_items=True)
    await coordinator.mark_running(me)
    return json.dumps({"success": True, "status": "resumed", "pending_consumed": pending})


@function_tool(timeout=120)
async def create_agent(
    ctx: RunContextWrapper,
    name: str,
    task: str,
    inherit_context: bool = True,
    skills: list[str] | None = None,
) -> str:
    """Spawn a focused specialist subagent (e.g. 'Auth Specialist', 'SQLi Prober') in parallel."""
    inner = _ctx(ctx)
    coordinator = coordinator_from_context(inner)
    parent_id = inner.get("agent_id")
    spawner = inner.get("spawn_child_agent")

    if coordinator is None or parent_id is None:
        return json.dumps({"success": False, "error": "Missing coordinator or parent agent ID"})

    if not callable(spawner):
        return json.dumps({"success": False, "error": "Child agent spawner not available in context"})

    try:
        res = await spawner(
            parent_ctx=inner,
            name=name,
            task=task,
            skills=list(skills or []),
            inherit_context=inherit_context,
        )
        return json.dumps(res, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Failed to spawn child agent '%s': %s", name, exc)
        return json.dumps({"success": False, "error": f"Failed to spawn agent: {exc}"})


@function_tool(timeout=30)
async def agent_finish(
    ctx: RunContextWrapper,
    result_summary: str,
    findings: list[str] | None = None,
    success: bool = True,
    final_recommendations: list[str] | None = None,
) -> str:
    """Subagent termination tool. Posts structured completion report to parent's inbox."""
    inner = _ctx(ctx)
    coordinator = coordinator_from_context(inner)
    me = inner.get("agent_id")
    parent_id = inner.get("parent_id")

    if coordinator is None or me is None:
        return json.dumps({"success": False, "error": "Missing coordinator context"})

    if parent_id is None:
        return json.dumps({
            "success": False,
            "error": "agent_finish is only for subagents. Root orchestrators must call finish_scan().",
        })

    if await coordinator.claim_parent_notice(me):
        async with coordinator._lock:
            agent_name = coordinator.names.get(me, me)
        report = _render_completion_report(
            agent_name=agent_name,
            agent_id=me,
            task=str(inner.get("task", "")),
            success=success,
            result_summary=result_summary,
            findings=list(findings or []),
            recommendations=list(final_recommendations or []),
        )
        await coordinator.send(parent_id, {
            "from": me,
            "type": "completion_report",
            "priority": "high",
            "content": report,
        })

    await coordinator.set_status(me, "completed" if success else "failed")
    return json.dumps({
        "success": True,
        "agent_completed": True,
        "message": f"Agent {me} finished and reported to parent {parent_id}.",
    })
