"""Watchdog tests: heartbeat persistence + health verdicts (5s liveness check)."""

from __future__ import annotations

import json
import time

import pytest

from rakshak.core.agents import AgentCoordinator
from rakshak.core.execution import _is_transient_provider_error
from rakshak.interface.viewer.agent_health import (
    compute_agent_health,
    summarize_health,
)


def test_transient_provider_error_markers() -> None:
    assert _is_transient_provider_error(Exception("[502] Service temporarily overloaded"))
    assert _is_transient_provider_error(Exception("Upstream request failed: [503] unavailable"))
    assert _is_transient_provider_error(Exception("connection reset by peer"))
    assert _is_transient_provider_error(Exception("request timed out after 30s"))
    assert not _is_transient_provider_error(ValueError("invalid tool argument: foo"))
    assert not _is_transient_provider_error(Exception("context window exceeded"))


def _state(**over: object) -> dict:
    base: dict = {"names": {}, "statuses": {}, "metadata": {}, "wait_kinds": {}, "errors": {}}
    base.update(over)
    return base


def test_running_fresh_heartbeat() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"a1": "Recon"},
        statuses={"a1": "running"},
        metadata={"a1": {"last_heartbeat": now - 10, "phase": "turn_ok", "turns": 4, "consecutive_errors": 0}},
    ), now=now)
    assert report[0]["verdict"] == "running"
    assert report[0]["seconds_since_heartbeat"] == pytest.approx(10, abs=1)


def test_degraded_on_consecutive_errors() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"a1": "SQLi"},
        statuses={"a1": "running"},
        metadata={"a1": {"last_heartbeat": now - 5, "consecutive_errors": 4}},
    ), now=now)
    assert report[0]["verdict"] == "degraded"


def test_stuck_suspected_on_stale_heartbeat() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"a1": "JWT"},
        statuses={"a1": "running"},
        metadata={"a1": {"last_heartbeat": now - 500, "phase": "loop", "turns": 9}},
    ), now=now, stuck_after_s=180)
    assert report[0]["verdict"] == "stuck_suspected"


def test_idle_early_warning_between_thresholds() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"a1": "Recon"},
        statuses={"a1": "running"},
        metadata={"a1": {"last_heartbeat": now - 75, "phase": "loop", "turns": 9}},
    ), now=now)
    assert report[0]["verdict"] == "idle"
    summary = summarize_health(report)
    assert summary["needs_attention"] is False
    assert summary["early_warning"] is True
    assert summary["watch"][0]["id"] == "a1"


def test_stuck_still_fires_above_threshold_with_custom_warn() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"a1": "JWT"},
        statuses={"a1": "running"},
        metadata={"a1": {"last_heartbeat": now - 500, "phase": "loop", "turns": 9}},
    ), now=now, warn_after_s=60, stuck_after_s=180)
    assert report[0]["verdict"] == "stuck_suspected"


def test_unknown_without_heartbeat() -> None:
    report = compute_agent_health(_state(
        names={"a1": "Fresh"}, statuses={"a1": "running"}, metadata={},
    ))
    assert report[0]["verdict"] == "unknown"


def test_waiting_failed_finished_paused() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"w": "W", "f": "F", "c": "C", "p": "P"},
        statuses={"w": "waiting", "f": "failed", "c": "completed", "p": "running"},
        wait_kinds={"w": "agents"},
        errors={"f": "boom"},
        metadata={"w": {}, "f": {}, "c": {}, "p": {}},
    ), now=now)
    by_id = {r["id"]: r for r in report}
    assert by_id["w"]["verdict"] == "waiting"
    assert by_id["f"]["verdict"] == "stopped"
    assert by_id["c"]["verdict"] == "finished"

    paused = compute_agent_health(_state(
        names={"p": "P"}, statuses={"p": "running"}, metadata={"p": {}},
        budget_stopped=True,
    ), now=now)
    assert paused[0]["verdict"] == "paused"


def test_summary_flags_attention() -> None:
    now = time.time()
    report = compute_agent_health(_state(
        names={"ok": "OK", "bad": "BAD"},
        statuses={"ok": "running", "bad": "failed"},
        metadata={"ok": {"last_heartbeat": now - 2}, "bad": {}},
        errors={"bad": "crashed hard"},
    ), now=now)
    summary = summarize_health(report)
    assert summary["total"] == 2
    assert summary["needs_attention"] is True
    assert summary["attention"][0]["id"] == "bad"


async def test_heartbeat_persists_to_snapshot(tmp_path) -> None:
    snap = tmp_path / "agents.json"
    coord = AgentCoordinator()
    coord.set_snapshot_path(snap)
    await coord.register("root_01", name="Root", parent_id=None, task="t", skills=[])
    await coord.touch_heartbeat("root_01", phase="loop", turns_taken=3, consecutive_errors=0)

    assert snap.exists()
    data = json.loads(snap.read_text(encoding="utf-8"))
    meta = data["metadata"]["root_01"]
    assert meta["phase"] == "loop"
    assert meta["turns"] == 3
    assert meta["last_heartbeat"] == pytest.approx(time.time(), abs=30)

    # Second rapid heartbeat updates memory without excess disk churn risk.
    await coord.touch_heartbeat("root_01", phase="turn_ok", turns_taken=4, consecutive_errors=0)
    assert coord.metadata["root_01"]["turns"] == 4


async def test_heartbeat_unknown_agent_is_noop(tmp_path) -> None:
    coord = AgentCoordinator()
    coord.set_snapshot_path(tmp_path / "agents.json")
    await coord.touch_heartbeat("ghost", phase="loop")  # must not raise
