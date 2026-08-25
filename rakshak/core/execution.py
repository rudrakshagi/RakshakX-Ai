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
from rakshak.core.hooks import ReportUsageHooks
from rakshak.core.sessions import (
    enforce_image_budget,
    open_agent_session,
    seed_initial_input,
)
from rakshak.llm.compaction import is_context_overflow, maybe_compact

logger = logging.getLogger(__name__)


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

    while turns_taken < max_turns:
        # Check if scan has been shut down or stopped
        if coordinator.budget_stopped:
            logger.info("Agent %s stopping due to global budget ceiling.", agent_id)
            break

        # Pace turns on low-TPM providers so each request fits a fresh rate window,
        # but skip the very first turn since no request has been issued yet.
        if turns_taken > 0:
            await _maybe_pace_turn(run_config)

        # Keep history well under the provider's per-request token cap.
        compacted = await maybe_compact(session, model=str(run_config.model), force=False)
        if compacted:
            logger.info("Agent %s compacted session proactively before turn.", agent_id)

        # Drain any incoming mailbox messages into the active SQLite session
        await coordinator.consume_pending(agent_id)
        await coordinator.mark_running(agent_id)

        try:
            # Enforce screenshot memory budget before model turn
            await enforce_image_budget(session, max_images=5)

            # Run SDK model turn
            result = await Runner.run(
                starting_agent=agent,
                input=current_input,
                session=session,
                run_config=run_config,
                context=context,
                max_turns=1,
            )
            turns_taken += 1
            if hooks:
                hooks.on_turn_complete(getattr(result, "usage", None))

            # Check if agent called a terminal lifecycle tool (finish_scan / agent_finish).
            # Use a truthy check: an empty string is NOT terminal, otherwise scans that
            # produce an empty final response get cut off mid-investigation.
            if result.final_output:
                logger.info("Agent %s reached terminal output: %s", agent_id, str(result.final_output)[:100])
                return result

            # Reset input for next turn (subsequent turns drive from session history)
            current_input = []

        except MaxTurnsExceeded as exc:
            # Per-turn SDK budget hit: the model made a tool call whose result is now
            # in the session; the outer loop drives the next SDK turn from history.
            logger.info(
                "Agent %s SDK turn budgeted (max_turns=1); continuing from session history (%s).",
                agent_id,
                exc,
            )
            turns_taken += 1
            current_input = []

        except Exception as exc:
            if is_context_overflow(exc):
                logger.warning("Context overflow detected on agent %s. Triggering compaction...", agent_id)
                compacted = await maybe_compact(
                    session,
                    model=str(run_config.model),
                    force=True,
                )
                if compacted:
                    continue
            delay = 2.0
            if _is_rate_limited(exc):
                delay = _rate_limit_backoff(exc)
                logger.warning(
                    "Rate limit on agent %s. Backing off %.1fs before retrying.",
                    agent_id,
                    delay,
                )
            logger.exception("Turn failed on agent %s: %s", agent_id, exc)
            await asyncio.sleep(delay)
            turns_taken += 1

    return None


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
) -> dict[str, Any]:
    """Instantiate, register, and launch a background child agent task."""
    child_id = uuid.uuid4().hex[:8]
    parent_id = parent_ctx.get("agent_id")

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
        **parent_ctx,
        "agent_id": child_id,
        "parent_id": parent_id,
        "task": task,
    }

    initial_input = [{"role": "user", "content": f"Your assigned objective: {task}"}]

    # Launch child agent loop in background
    task_coro = run_agent_loop(
        agent=child_agent,
        initial_input=initial_input,
        run_config=run_config,
        context=child_context,
        max_turns=max_turns,
        coordinator=coordinator,
        agent_id=child_id,
        session=child_session,
    )
    async_task = asyncio.create_task(task_coro)
    await coordinator.attach_runtime(child_id, task=async_task)

    return {
        "success": True,
        "agent_id": child_id,
        "name": name,
        "status": "spawned_and_running",
    }
