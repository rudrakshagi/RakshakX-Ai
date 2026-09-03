"""Unit tests for the agent execution loop."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from agents import RunConfig

from rakshak.core.execution import (
    MAX_CHILDREN,
    _count_children,
    _get_depth,
    _is_rate_limited,
    _rate_limit_backoff,
    run_agent_loop,
    spawn_child_agent,
)
from rakshak.core.sessions import open_agent_session


def test_is_rate_limited_on_ratelimit_text():
    assert _is_rate_limited(Exception("rate_limit exceeded")) is True


def test_is_rate_limited_on_try_again_seconds():
    assert _is_rate_limited(Exception("please try again in 5.0s")) is True


def test_is_rate_limited_false():
    assert _is_rate_limited(Exception("boom")) is False


def test_rate_limit_backoff_parses_seconds():
    # Backoff floors at 65s regardless of parsed value.
    exc = Exception("please try again in 10.0s")
    assert _rate_limit_backoff(exc) == 65.0


def test_rate_limit_backoff_min_65():
    exc = Exception("please try again in 1.0s")
    assert _rate_limit_backoff(exc) >= 65.0


async def _make_agent(tmp_path, coord, agent_id):
    db = tmp_path / "agents.db"
    session = open_agent_session(agent_id, db)
    return session


@pytest.mark.asyncio
async def test_run_agent_loop_terminal_output_returns(tmp_path):
    from rakshak.core.agents import AgentCoordinator
    from tests.conftest import FakeRunResult

    coordinator = AgentCoordinator()
    await coordinator.register("root01", "Root", parent_id=None)
    session = await _make_agent(tmp_path, coordinator, "root01")

    run_config = RunConfig(model="test/gpt-4o", model_provider=None)
    agent = None

    result = FakeRunResult(final_output="done")

    with patch("rakshak.core.execution.Runner.run", AsyncMock(return_value=result)) as mock_run:
        out = await run_agent_loop(
            agent=agent,
            initial_input="begin",
            run_config=run_config,
            context={"agent_id": "root01"},
            max_turns=5,
            coordinator=coordinator,
            agent_id="root01",
            session=session,
        )
    mock_run.assert_awaited()
    assert out is result


@pytest.mark.asyncio
async def test_run_agent_loop_breaks_on_budget_stop(tmp_path):
    from rakshak.core.agents import AgentCoordinator

    coordinator = AgentCoordinator()
    await coordinator.register("root01", "Root", parent_id=None)
    await coordinator.trigger_budget_stop()
    session = await _make_agent(tmp_path, coordinator, "root01")

    run_config = RunConfig(model="test/gpt-4o", model_provider=None)

    with patch("rakshak.core.execution.Runner.run", AsyncMock()) as mock_run:
        out = await run_agent_loop(
            agent=None,
            initial_input="begin",
            run_config=run_config,
            context={},
            max_turns=5,
            coordinator=coordinator,
            agent_id="root01",
            session=session,
        )
    mock_run.assert_not_awaited()
    assert out is None


@pytest.mark.asyncio
async def test_spawn_child_agent_limits(tmp_path):
    from rakshak.core.agents import AgentCoordinator

    coordinator = AgentCoordinator()
    await coordinator.register("root01", "Root", parent_id=None)
    db = tmp_path / "agents.db"

    parent_ctx = {"agent_id": "root01", "coordinator": coordinator}
    factory = lambda **kw: None  # noqa: E731

    # Register many children to exceed the cap
    for i in range(MAX_CHILDREN + 1):
        await coordinator.register(f"child{i}", f"Child{i}", parent_id="root01")

    with patch("rakshak.core.execution.run_agent_loop", AsyncMock()):
        res = await spawn_child_agent(
            coordinator=coordinator,
            factory=factory,
            agents_db_path=db,
            sessions_to_close=[],
            run_config=RunConfig(model="test/gpt-4o", model_provider=None),
            max_turns=150,
            parent_ctx=parent_ctx,
            name="overflow",
            task="task",
            skills=[],
        )
    assert res["success"] is False
    assert "Max children" in res["error"]


@pytest.mark.asyncio
async def test_count_children_counts_direct():
    from rakshak.core.agents import AgentCoordinator

    coordinator = AgentCoordinator()
    await coordinator.register("root01", "Root", parent_id=None)
    await coordinator.register("c1", "C1", parent_id="root01")
    await coordinator.register("c2", "C2", parent_id="root01")
    await coordinator.register("gc", "GC", parent_id="c1")
    assert await _count_children(coordinator, "root01") == 2
    assert await _count_children(coordinator, "c1") == 1


@pytest.mark.asyncio
async def test_get_depth():
    from rakshak.core.agents import AgentCoordinator

    coordinator = AgentCoordinator()
    await coordinator.register("root01", "Root", parent_id=None)
    await coordinator.register("c1", "C1", parent_id="root01")
    await coordinator.register("gc", "GC", parent_id="c1")
    assert await _get_depth(coordinator, "root01") == 0
    assert await _get_depth(coordinator, "c1") == 1
    assert await _get_depth(coordinator, "gc") == 2
