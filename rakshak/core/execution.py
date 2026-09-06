"""Execution loop for multi-agent dynamic pentesting."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from rakshak.core.agents import AgentCoordinator, heartbeat_scope
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

# Final-phase window: the last N turns are reserved for filing findings and
# closing out — no new long-running scans. Reminders fire at these marks.
FINAL_PHASE_WINDOW = 10
FINAL_PHASE_MARKS = (10, 5, 2)


def final_phase_notice(turns_left: int) -> str:
    """Build the operator reminder injected when the turn budget runs low."""
    return (
        f"[FINAL PHASE — {turns_left} turns left] Do NOT start new long-running "
        "scans (no ffuf/nmap-full/nuclei-full/dirsearch sweeps, no `find /` hunts). "
        "Work only with evidence already collected: file every confirmed finding "
        "with create_vulnerability_report NOW, then call finish_scan with all four "
        "narrative sections filled honestly (including what failed or stayed "
        "unverified). A finished honest report beats an unfinished deep scan."
    )


@contextlib.asynccontextmanager
async def agent_heartbeat_ticker(
    coordinator: AgentCoordinator,
    agent_id: str,
    turns_taken: int = 0,
    interval: float = 3.0,
):
    """Background context manager that ticks agent heartbeat continuously during tool execution."""
    stop_event = asyncio.Event()

    async def _ticker():
        while not stop_event.is_set():
            with contextlib.suppress(Exception):
                await coordinator.touch_heartbeat(
                    agent_id,
                    phase="executing_tool",
                    turns_taken=turns_taken,
                )
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.sleep(interval)

    task = asyncio.create_task(_ticker())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        with contextlib.suppress(Exception, asyncio.CancelledError):
            await task


def _is_transient_provider_error(exc: Exception) -> bool:
    """True for retryable upstream failures that must not burn turn budget.

    Observed in the wild: Nvidia-backed free models flap with
    ``[502] Service temporarily overloaded`` / 503s mid-scan. Each such error
    used to cost a full turn (``turns_taken += 1``), so 27 upstream 502s ate
    most of a 60-turn budget and the agent never reached exploitation.
    Transient errors still count toward ``consecutive_errors`` (the 10-strike
    guard stays), they just don't consume a turn.
    """
    text = f"{type(exc).__name__} {exc}".lower()
    markers = (
        "502", "503", "504",
        "overloaded", "over capacity",
        "temporarily unavailable", "try again",
        "timeout", "timed out", "connection reset",
        "connection aborted", "service unavailable",
    )
    return any(m in text for m in markers)


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


def _steer_fingerprint(item: dict[str, Any]) -> str:
    """Stable id for a steer queue entry (queue has no ids; capped at last-50)."""
    return f"{item.get('iso', '')}|{item.get('timestamp', '')}|{item.get('instruction', '')}"


def poll_steer_queue(
    state_dir: Any, since_index: int = 0
) -> tuple[list[dict[str, Any]], int]:
    """Read new steer instructions appended since ``since_index``.

    Returns ``(new_items, next_index)`` where ``next_index`` is the current
    queue length. Truncation-safe: if the queue was capped to the last 50
    entries and ``since_index`` points past the current list, the caller
    should fall back to fingerprint dedupe (handled in ``run_agent_loop``).
    Never raises — returns ``([], since_index)`` on any failure.
    """
    try:
        since = max(int(since_index or 0), 0)
    except Exception:
        since = 0
    try:
        steer_file = Path(str(state_dir)) / "steer_queue.json"
        if not steer_file.exists():
            return [], since
        data = json.loads(steer_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return [], since
        next_index = len(data)
        if since >= next_index:
            # No new items by count (covers both idle and capped-rotation
            # cases; rotation is caught via fingerprint scan in the loop).
            return [], next_index
        new_items = [d for d in data[since:] if isinstance(d, dict)]
        return new_items, next_index
    except Exception:
        return [], since


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
    announced_final_marks: set[int] = set()
    # Live operator-steer state (dedupe via fingerprint set; index fast-path).
    try:
        consumed = context.get("consumed_steer_ids")
        if not isinstance(consumed, set):
            consumed = set(consumed) if isinstance(consumed, (list, tuple)) else set()
            context["consumed_steer_ids"] = consumed
    except Exception:
        consumed = set()

    def _resolve_steer_dir() -> Path | None:
        try:
            for key in ("state_dir", "runtime_state_dir", "runtime_state"):
                val = context.get(key)
                if val:
                    return Path(str(val))
            # Derive from agents db path: <state_dir>/agents.db
            db_path = context.get("agents_db_path")
            if db_path:
                return Path(str(db_path)).parent
        except Exception:
            pass
        return None

    while turns_taken < max_turns:
        if coordinator.budget_stopped:
            logger.info("Agent %s stopping due to global budget ceiling.", agent_id)
            break

        if turns_taken > 0:
            await _maybe_pace_turn(run_config)

        compacted = await maybe_compact(session, model=str(run_config.model), force=False)
        if compacted:
            logger.info("Agent %s compacted session proactively before turn.", agent_id)

        # Live operator steer: poll steer_queue.json BEFORE consume_pending so
        # self-addressed instructions are drained into the session this turn.
        # Failures must never break the loop.
        try:
            steer_dir = _resolve_steer_dir()
            if steer_dir is not None:
                since_index = context.get("steer_index", 0)
                try:
                    since_index = int(since_index or 0)
                except Exception:
                    since_index = 0
                new_items, next_index = poll_steer_queue(steer_dir, since_index)
                # Truncation-safe fallback: queue is capped at last-50, so a
                # count-based slice can miss rotation. Full-scan filter by
                # fingerprint catches any unconsumed entry.
                if not new_items:
                    with contextlib.suppress(Exception):
                        full, full_next = poll_steer_queue(steer_dir, 0)
                        next_index = full_next
                        new_items = [d for d in full if _steer_fingerprint(d) not in consumed]
                pending_steer: list[str] = []
                for item in new_items:
                    try:
                        fp = _steer_fingerprint(item)
                        if fp in consumed:
                            continue
                        consumed.add(fp)
                        target = item.get("target_agent_id") or item.get("target") or ""
                        if target and str(target) not in (agent_id, str(context.get("agent_name", "")), "root", "all", "*"):
                            # Not addressed to this agent — mark consumed to
                            # avoid re-scanning, but don't inject.
                            continue
                        instruction = str(item.get("instruction", "")).strip()
                        if not instruction:
                            continue
                        pending_steer.append(instruction)
                    except Exception:
                        continue
                context["steer_index"] = next_index
                for instruction in pending_steer:
                    msg = {
                        "from": "user",
                        "type": "steer",
                        "priority": "high",
                        "content": f"[OPERATOR STEER] {instruction}",
                    }
                    try:
                        delivered = await coordinator.send(agent_id, msg)
                    except Exception:
                        delivered = False
                    if not delivered:
                        # Fallback: prepend to next turn input (last-50 safe).
                        try:
                            steer_item = {"role": "user", "content": f"[OPERATOR STEER] {instruction}"}
                            if isinstance(current_input, list):
                                current_input = ([steer_item] + current_input)[-50:]
                            else:
                                current_input = [steer_item]
                        except Exception:
                            pass
        except Exception:
            logger.debug("Steer polling failed for agent %s; continuing.", agent_id, exc_info=True)
        await coordinator.consume_pending(agent_id)
        if coordinator.statuses.get(agent_id) != "running":
            await coordinator.mark_running(agent_id)
        # Final-phase guard: when the turn budget runs low, inject an
        # operator reminder so the agent stops starting new long scans and
        # instead files findings + finishes. Fires at 10/5/2 turns left.
        try:
            turns_left = max_turns - turns_taken
            for mark in FINAL_PHASE_MARKS:
                if turns_left <= mark and mark not in announced_final_marks:
                    announced_final_marks.add(mark)
                    notice = {"role": "user", "content": final_phase_notice(turns_left)}
                    if isinstance(current_input, list):
                        current_input = [*current_input, notice][-50:]
                    else:
                        current_input = [notice]
                    context["final_phase"] = True
        except Exception:
            logger.debug("Final-phase notice failed for agent %s; continuing.", agent_id, exc_info=True)
        # Liveness heartbeat so the 5s UI watchdog can detect stuck/stopped
        # agents. Failures must never break the loop.
        with contextlib.suppress(Exception):
            await coordinator.touch_heartbeat(
                agent_id, phase="loop", turns_taken=turns_taken,
                consecutive_errors=consecutive_errors,
            )

        try:
            await enforce_image_budget(session, max_images=5)

            # Bind the ambient heartbeat scope so deep paths (sandbox exec)
            # attribute their heartbeats to this agent even with concurrent
            # specialists turning. The ticker keeps last_heartbeat fresh while
            # tools run; to_thread exec (sdk_session) keeps the loop free.
            async with heartbeat_scope(coordinator, agent_id):
                async with agent_heartbeat_ticker(coordinator, agent_id, turns_taken=turns_taken):
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
            with contextlib.suppress(Exception):
                await coordinator.touch_heartbeat(
                    agent_id, phase="turn_ok", turns_taken=turns_taken,
                    consecutive_errors=0, exec_detail="",
                )

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
            with contextlib.suppress(Exception):
                await coordinator.touch_heartbeat(
                    agent_id, phase="loop", turns_taken=turns_taken,
                    exec_detail="",
                )

        except Exception as exc:
            consecutive_errors += 1
            if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                logger.error(
                    "Agent %s exceeded %d consecutive errors. Marking as failed.",
                    agent_id,
                    _MAX_CONSECUTIVE_ERRORS,
                )
                await coordinator.set_status(agent_id, "failed", error=str(exc))
                # Raise (don't silently break) so the scan reports Failed in
                # run_meta instead of a misleading Completed with 0 findings.
                raise RuntimeError(
                    f"Agent {agent_id} failed after {consecutive_errors} consecutive errors: {exc}"
                ) from exc

            if is_context_overflow(exc):
                logger.warning("Context overflow on agent %s. Triggering compaction...", agent_id)
                compacted = await maybe_compact(session, model=str(run_config.model), force=True)
                if compacted:
                    continue
                logger.error("Compaction failed on agent %s. Marking as failed.", agent_id)
                await coordinator.set_status(agent_id, "failed", error="Context overflow, compaction failed")
                raise RuntimeError(f"Agent {agent_id} failed: context overflow, compaction failed") from exc

            delay = 2.0
            transient = _is_transient_provider_error(exc)
            if _is_rate_limited(exc):
                delay = _rate_limit_backoff(exc)
                logger.warning(
                    "Rate limit on agent %s. Backing off %.1fs before retrying.",
                    agent_id,
                    delay,
                )
                with contextlib.suppress(Exception):
                    await coordinator.touch_heartbeat(
                        agent_id, phase="backing_off", turns_taken=turns_taken,
                        consecutive_errors=consecutive_errors,
                    )
            else:
                if transient:
                    logger.warning(
                        "Transient provider error on agent %s (no turn consumed): %s",
                        agent_id, str(exc)[:200],
                    )
                else:
                    logger.exception("Turn failed on agent %s: %s", agent_id, exc)
                with contextlib.suppress(Exception):
                    await coordinator.touch_heartbeat(
                        agent_id, phase="error", turns_taken=turns_taken,
                        consecutive_errors=consecutive_errors,
                    )
            await asyncio.sleep(delay)
            if not transient:
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
    # Propagate steer-queue location so child loops can poll operator input.
    for _k in ("state_dir", "runtime_state_dir", "agents_db_path"):
        if _k in parent_ctx:
            child_context[_k] = parent_ctx[_k]
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
