"""Execution loop for multi-agent dynamic pentesting."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable
from typing import Any

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from rakshak.core.agents import AgentCoordinator
from rakshak.core.hooks import BudgetExceededError, ReportUsageHooks
from rakshak.core.sessions import (
    enforce_image_budget,
    open_agent_session,
    seed_initial_input,
    strip_all_images_from_session,
)
from rakshak.llm.compaction import is_context_overflow, maybe_compact
from rakshak.llm.stuck_detector import StuckDetector

logger = logging.getLogger(__name__)

MAX_CHILDREN = 8
MAX_CHILD_DEPTH = 2
_MAX_CONSECUTIVE_ERRORS = 10


def _is_rate_limited(exc: Exception) -> bool:
    import re

    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "ratelimit" in name or "rate_limit" in text:
        return True
    match = re.search(r"please try again in (\d+(?:\.\d+)?)s", text)
    return match is not None


def _rate_limit_backoff(exc: Exception) -> float:
    import re

    match = re.search(r"please try again in (\d+(?:\.\d+)?)s", str(exc))
    if match:
        return max(float(match.group(1)) + 3.0, 65.0)
    return 65.0


def _maybe_pace_turn(run_config: RunConfig) -> Awaitable[None]:
    """Wait so consecutive turns land in separate provider rate-limit windows."""
    model = str(getattr(run_config, "model", ""))
    if not model.startswith("groq/"):
        return asyncio.sleep(0)

    return asyncio.sleep(30.0)


async def run_agent_loop(
    *,
    agent: Any,
    initial_input: Any,
    run_config: RunConfig,
    context: dict[str, Any],
    max_turns: int = 150,
    coordinator: AgentCoordinator,
    agent_id: str,
    session: Any,
    hooks: ReportUsageHooks | None = None,
) -> Any:
    """Execute the turn-by-turn reasoning and tool-execution loop for an agent."""
    await seed_initial_input(session, initial_input)

    current_input: Any = []
    turns_taken = 0
    stuck = StuckDetector()
    consecutive_errors = 0

    while turns_taken < max_turns:
        if coordinator.budget_stopped:
            logger.info("Agent %s stopping due to global budget ceiling.", agent_id)
            break

        if turns_taken > 0:
            await _maybe_pace_turn(run_config)

        compacted = await maybe_compact(session, model=str(run_config.model), force=False)
        if compacted:
            logger.info("Agent %s compacted session proactively before turn.", agent_id)

        await coordinator.consume_pending(agent_id)
        if coordinator.statuses.get(agent_id) != "running":
            await coordinator.mark_running(agent_id)

        try:
            await enforce_image_budget(session, max_images=5)

            result = await Runner.run(
                starting_agent=agent,
                input=current_input,
                session=session,
                run_config=run_config,
                context=context,
                max_turns=1,
            )
            turns_taken += 1
            consecutive_errors = 0
            stuck.reset_unknown_count()

            if hooks:
                hooks.on_turn_complete(getattr(result, "usage", None))

            if result.final_output:
                logger.info("Agent %s reached terminal output: %s", agent_id, str(result.final_output)[:100])
                return result

            current_input = []

        except BudgetExceededError:
            logger.warning("Agent %s hit budget ceiling. Stopping.", agent_id)
            await coordinator.trigger_budget_stop()
            break

        except MaxTurnsExceeded as exc:
            logger.info(
                "Agent %s SDK turn budgeted (max_turns=1); continuing from session history (%s).",
                agent_id,
                exc,
            )
            turns_taken += 1
            current_input = []

        except Exception as exc:
            consecutive_errors += 1
            if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                logger.error(
                    "Agent %s exceeded %d consecutive errors. Marking as failed.",
                    agent_id,
                    _MAX_CONSECUTIVE_ERRORS,
                )
                await coordinator.set_status(agent_id, "failed", error=str(exc))
                break

            if is_context_overflow(exc):
                logger.warning("Context overflow on agent %s. Triggering compaction...", agent_id)
                compacted = await maybe_compact(session, model=str(run_config.model), force=True)
                if compacted:
                    continue
                logger.error("Compaction failed on agent %s. Marking as failed.", agent_id)
                await coordinator.set_status(agent_id, "failed", error="Context overflow, compaction failed")
                break

            delay = 2.0
            if _is_rate_limited(exc):
                delay = _rate_limit_backoff(exc)
                logger.warning(
                    "Rate limit on agent %s. Backing off %.1fs before retrying.",
                    agent_id,
                    delay,
                )
            else:
                logger.exception("Turn failed on agent %s: %s", agent_id, exc)
            await asyncio.sleep(delay)
            turns_taken += 1

    return None


async def _count_children(coordinator: AgentCoordinator, parent_id: str) -> int:
    """Count direct children of a parent agent."""
    _, _, _, _ = await coordinator.graph_snapshot()
    async with coordinator._lock:
        return sum(1 for p in coordinator.parent_of.values() if p == parent_id)


async def _get_depth(coordinator: AgentCoordinator, agent_id: str) -> int:
    """Compute depth in the agent tree (root=0)."""
    depth = 0
    current: str | None = agent_id
    async with coordinator._lock:
        while (current is not None) and (coordinator.parent_of.get(current) is not None):
            parent = coordinator.parent_of[current]
            current = parent
            depth += 1
            if depth > MAX_CHILD_DEPTH + 1:
                break
    return depth


async def spawn_child_agent(
    *,
    coordinator: AgentCoordinator,
    factory: Any,
    agents_db_path: Any,
    sessions_to_close: list[Any],
    run_config: RunConfig,
    max_turns: int = 150,
    parent_ctx: dict[str, Any],
    name: str,
    task: str,
    skills: list[str],
    inherit_context: bool = True,
    hooks: ReportUsageHooks | None = None,
) -> dict[str, Any]:
    """Instantiate, register, and launch a background child agent task."""
    parent_id = parent_ctx.get("agent_id")
    parent_id = str(parent_id) if parent_id is not None else None
    if parent_id is None:
        return {"success": False, "error": "No parent agent in context"}

    child_count = await _count_children(coordinator, parent_id)
    if child_count >= MAX_CHILDREN:
        return {"success": False, "error": f"Max children ({MAX_CHILDREN}) reached for agent {parent_id}"}

    depth = await _get_depth(coordinator, parent_id)
    if depth >= MAX_CHILD_DEPTH:
        return {"success": False, "error": f"Max agent depth ({MAX_CHILD_DEPTH}) reached"}

    child_id = uuid.uuid4().hex[:8]

    await coordinator.register(
        child_id,
        name=name,
        parent_id=parent_id,
        task=task,
        skills=skills,
    )

    child_session = open_agent_session(child_id, agents_db_path)
    sessions_to_close.append(child_session)
    await coordinator.attach_runtime(child_id, session=child_session)

    child_agent = factory(name=name, skills=skills)

    child_context = {
        "coordinator": coordinator,
        "agent_id": child_id,
        "parent_id": parent_id,
        "task": task,
        "spawn_child_agent": parent_ctx.get("spawn_child_agent"),
    }
    if inherit_context:
        for key in ("sandbox_session", "caido_client"):
            if key in parent_ctx:
                child_context[key] = parent_ctx[key]
    else:
        await strip_all_images_from_session(child_session)

    initial_input = [{"role": "user", "content": f"Your assigned objective: {task}"}]

    task_coro = run_agent_loop(
        agent=child_agent,
        initial_input=initial_input,
        run_config=run_config,
        context=child_context,
        max_turns=max_turns,
        coordinator=coordinator,
        agent_id=child_id,
        session=child_session,
        hooks=hooks,
    )
    async_task = asyncio.create_task(task_coro)
    await coordinator.attach_runtime(child_id, task=async_task)

    return {
        "success": True,
        "agent_id": child_id,
        "name": name,
        "status": "spawned_and_running",
    }
