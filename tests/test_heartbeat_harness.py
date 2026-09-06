"""Unit tests for the Phase-1 heartbeat harness.

Covers:
- ``rakshak/runtime/sdk_session.py``: ``_exec_internal`` publishes a truncated
  command via the ambient heartbeat scope and runs blocking
  ``docker_client.exec_command`` in a worker thread; ``running()`` runs
  ``container.reload`` in a worker thread.
- ``rakshak/core/agents.py``: ``heartbeat_scope`` / ``current_heartbeat_scope``
  plus ``touch_heartbeat(..., exec_detail=...)`` set/clear/leave semantics.
- ``rakshak/interface/viewer/agent_health.py``: ``exec`` passthrough into
  report entries and `` :: <exec>`` detail suffix.

All docker interactions are mocked (blocking ``time.sleep`` simulates the old
event-loop freeze); no real container is required.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

from rakshak.core.agents import (
    AgentCoordinator,
    current_heartbeat_scope,
    heartbeat_scope,
)
from rakshak.core.execution import agent_heartbeat_ticker
from rakshak.interface.viewer.agent_health import compute_agent_health
from rakshak.runtime.sdk_session import SDKSandboxSession


def _make_session(block_s: float = 0.0, output: str = "ok") -> SDKSandboxSession:
    container = MagicMock()
    docker_client = MagicMock()

    def _exec(*args, **kwargs):
        if block_s:
            time.sleep(block_s)
        return (0, output)

    docker_client.exec_command.side_effect = _exec
    return SDKSandboxSession(container=container, docker_client=docker_client)


async def _register(coord: AgentCoordinator, agent_id: str = "a1") -> None:
    await coord.register(agent_id, name=agent_id, parent_id=None, task="t", skills=[])


# 1. Ticker keeps ticking through a blocked exec -----------------------------
async def test_ticker_keeps_ticking_during_blocked_exec() -> None:
    """Heartbeat must advance WHILE exec_command blocks (~3s).

    Fails on the old synchronous code (event loop frozen, ticker starves);
    passes now that exec runs via asyncio.to_thread.
    """
    coord = AgentCoordinator()
    await _register(coord)
    session = _make_session(block_s=3.0)

    hb_times: list[float] = []
    orig_touch = coord.touch_heartbeat

    async def spy(agent_id: str, **kw) -> None:
        hb_times.append(time.time())
        await orig_touch(agent_id, **kw)

    coord.touch_heartbeat = spy  # type: ignore[method-assign]

    async with heartbeat_scope(coord, "a1"):
        async with agent_heartbeat_ticker(coord, "a1", interval=1.0):
            await asyncio.sleep(0.1)  # let the ticker tick once pre-exec
            hb_times.clear()
            exec_start = time.time()
            result = await session._exec_internal("sleep", "3")
            exec_end = time.time()

    assert result.exit_code == 0
    during = [t for t in hb_times if exec_start <= t <= exec_end]
    assert len(during) >= 1, (
        f"no heartbeat ticked during a 3s blocked exec "
        f"({len(hb_times)} ticks total) — event loop was frozen"
    )
    # No silent gap longer than ticker interval + slack across the exec window.
    window = sorted([exec_start, *during, exec_end])
    gaps = [b - a for a, b in zip(window, window[1:])]
    assert max(gaps) < 6.0, f"heartbeat gap too large during exec: {gaps}"
    # last_heartbeat itself advanced into the exec window.
    assert coord.metadata["a1"]["last_heartbeat"] >= exec_start


# 2. exec_detail is published (and truncated) ---------------------------------
async def test_exec_detail_set_and_truncated() -> None:
    coord = AgentCoordinator()
    await _register(coord)
    session = _make_session()

    async with heartbeat_scope(coord, "a1"):
        await session._exec_internal("ffuf", "-u", "http://target/FUZZ")
    assert "ffuf" in coord.metadata["a1"]["exec"]
    assert "http://target/FUZZ" in coord.metadata["a1"]["exec"]

    long_cmd = "ffuf " + "A" * 200
    assert len(long_cmd) > 120
    async with heartbeat_scope(coord, "a1"):
        await session._exec_internal(long_cmd)
    assert len(coord.metadata["a1"]["exec"]) <= 120
    assert coord.metadata["a1"]["exec"].startswith("ffuf ")


async def test_exec_internal_without_scope_leaves_no_exec() -> None:
    coord = AgentCoordinator()
    await _register(coord)
    assert current_heartbeat_scope() is None
    session = _make_session()
    # No scope bound: must not raise and must not invent metadata.
    await session._exec_internal("echo", "hi")
    assert "exec" not in coord.metadata["a1"]


# 3. exec_detail clear semantics ----------------------------------------------
async def test_exec_detail_clear_semantics() -> None:
    coord = AgentCoordinator()
    await _register(coord)

    await coord.touch_heartbeat("a1", phase="executing_tool", exec_detail="ffuf ...")
    assert coord.metadata["a1"]["exec"] == "ffuf ..."

    # No exec_detail -> untouched (so the 3s ticker never wipes the display).
    await coord.touch_heartbeat("a1", phase="executing_tool")
    assert coord.metadata["a1"]["exec"] == "ffuf ..."

    # Empty string clears.
    await coord.touch_heartbeat("a1", phase="loop", exec_detail="")
    assert "exec" not in coord.metadata["a1"]


# 4. Scope isolation -----------------------------------------------------------
async def test_scope_isolation() -> None:
    coord = AgentCoordinator()
    await _register(coord, "agent_a")
    await _register(coord, "agent_b")

    assert current_heartbeat_scope() is None

    async with heartbeat_scope(coord, "agent_a"):
        scope = current_heartbeat_scope()
        assert scope is not None
        scoped_coord, scoped_id = scope
        assert scoped_id == "agent_a"
        await scoped_coord.touch_heartbeat(
            scoped_id, phase="executing_tool", exec_detail="nmap fast"
        )
        # Nested scope binds the inner agent, then restores the outer one.
        async with heartbeat_scope(coord, "agent_b"):
            assert current_heartbeat_scope()[1] == "agent_b"  # type: ignore[index]
        assert current_heartbeat_scope()[1] == "agent_a"  # type: ignore[index]

    assert coord.metadata["agent_a"]["exec"] == "nmap fast"
    assert "exec" not in coord.metadata.get("agent_b", {})
    assert current_heartbeat_scope() is None


# 5. Health passthrough --------------------------------------------------------
def _health_state(now: float, agent_id: str, meta: dict) -> dict:
    return {
        "names": {agent_id: agent_id},
        "statuses": {agent_id: "running"},
        "metadata": {agent_id: meta},
        "wait_kinds": {},
        "errors": {},
    }


def test_health_exec_passthrough() -> None:
    now = time.time()
    cases = [
        # (meta, expected verdict)
        ({"last_heartbeat": now - 5, "phase": "turn_ok", "turns": 4}, "running"),
        ({"last_heartbeat": now - 75, "phase": "loop", "turns": 9}, "idle"),
        ({"last_heartbeat": now - 500, "phase": "loop", "turns": 9}, "stuck_suspected"),
        ({"last_heartbeat": now - 5, "consecutive_errors": 4}, "degraded"),
    ]
    for meta, verdict in cases:
        meta = {**meta, "exec": "ffuf -u http://target/FUZZ"}
        report = compute_agent_health(_health_state(now, "a1", meta), now=now)
        entry = report[0]
        assert entry["verdict"] == verdict
        assert entry["exec"] == "ffuf -u http://target/FUZZ"
        assert "ffuf -u http://target/FUZZ" in entry["detail"]
        assert "::" in entry["detail"]


def test_health_without_exec_has_no_suffix() -> None:
    now = time.time()
    report = compute_agent_health(
        _health_state(
            now, "a1", {"last_heartbeat": now - 5, "phase": "turn_ok", "turns": 1}
        ),
        now=now,
    )
    entry = report[0]
    assert entry["verdict"] == "running"
    assert entry["exec"] is None
    assert "::" not in entry["detail"]


# 6. running() stays off the event loop ----------------------------------------
async def test_running_uses_to_thread_stays_responsive() -> None:
    container = MagicMock()
    container.status = "running"
    container.reload.side_effect = lambda: time.sleep(2.0)
    session = SDKSandboxSession(container=container, docker_client=MagicMock())

    tick_at: dict[str, float] = {}
    start = time.monotonic()

    async def marker() -> None:
        await asyncio.sleep(0.2)
        tick_at["t"] = time.monotonic()

    ok, _ = await asyncio.gather(session.running(), marker())
    assert ok is True
    # The 0.2s sleep fired long before the 2s blocking reload finished,
    # proving reload ran off the event loop.
    assert tick_at["t"] - start < 1.5


async def test_running_bool_variants() -> None:
    session = SDKSandboxSession(container=MagicMock(), docker_client=MagicMock())

    session._container.status = "running"
    session._container.reload = MagicMock()
    assert await session.running() is True

    session._container.status = "exited"
    session._container.reload = MagicMock()
    assert await session.running() is False

    session._container.reload = MagicMock(side_effect=Exception("gone"))
    assert await session.running() is False
