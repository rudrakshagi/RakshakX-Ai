"""Unit tests for AgentCoordinator multi-agent graph and mailbox messaging."""

from __future__ import annotations

import pytest

from rakshak.core.agents import AgentCoordinator


@pytest.mark.asyncio
async def test_coordinator_registration_and_tree():
    coord = AgentCoordinator()

    await coord.register("root01", "Root Orchestrator", parent_id=None)
    await coord.register("child01", "SQLi Specialist", parent_id="root01", task="Test SQLi")

    parent_of, statuses, names, _ = await coord.graph_snapshot()

    assert parent_of["root01"] is None
    assert parent_of["child01"] == "root01"
    assert statuses["root01"] == "running"
    assert statuses["child01"] == "running"
    assert names["child01"] == "SQLi Specialist"


@pytest.mark.asyncio
async def test_coordinator_mailbox_delivery():
    coord = AgentCoordinator()

    await coord.register("root01", "Root Orchestrator", parent_id=None)
    await coord.register("child01", "Auth Specialist", parent_id="root01")

    delivered = await coord.send("child01", {
        "from": "root01",
        "content": "Focus on /api/v1/auth/jwt",
        "type": "instruction",
    })
    assert delivered is True

    count, _ = await coord.consume_pending("child01")
    assert count == 1

    count_empty, _ = await coord.consume_pending("child01")
    assert count_empty == 0


@pytest.mark.asyncio
async def test_coordinator_snapshot_and_restore():
    coord = AgentCoordinator()
    await coord.register("root01", "Root Orchestrator", parent_id=None)
    await coord.set_status("root01", "completed")

    snap = await coord.snapshot()
    assert snap["statuses"]["root01"] == "completed"

    new_coord = AgentCoordinator()
    await new_coord.restore(snap)
    assert new_coord.statuses["root01"] == "completed"


@pytest.mark.asyncio
async def test_trigger_budget_stop_wakes_all():
    coord = AgentCoordinator()
    await coord.register("root01", "Root", parent_id=None)
    await coord.register("child01", "Child", parent_id="root01")

    await coord.trigger_budget_stop()
    assert coord.budget_stopped is True
    assert coord.runtimes["root01"].wake.is_set()
    assert coord.runtimes["child01"].wake.is_set()


@pytest.mark.asyncio
async def test_claim_parent_notice_idempotent():
    coord = AgentCoordinator()
    await coord.register("child01", "Child", parent_id="root01")
    assert await coord.claim_parent_notice("child01") is True
    assert await coord.claim_parent_notice("child01") is False


@pytest.mark.asyncio
async def test_wait_for_message_returns_true_on_pending():
    coord = AgentCoordinator()
    await coord.register("root01", "Root", parent_id=None)
    await coord.send("root01", {"from": "child01", "content": "hi"})
    assert await coord.wait_for_message("root01", timeout=1.0) is True


@pytest.mark.asyncio
async def test_wait_for_message_timeout():
    coord = AgentCoordinator()
    await coord.register("root01", "Root", parent_id=None)
    assert await coord.wait_for_message("root01", timeout=0.05) is False


@pytest.mark.asyncio
async def test_cancel_descendants():
    import asyncio

    coord = AgentCoordinator()
    await coord.register("root01", "Root", parent_id=None)
    await coord.register("child01", "Child", parent_id="root01", task="x")

    async def sleeper():
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise

    task = asyncio.create_task(sleeper())
    await coord.attach_runtime("child01", task=task)
    await coord.cancel_descendants("root01")
    assert task.cancelled()
