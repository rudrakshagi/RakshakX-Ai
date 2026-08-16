"""Unit tests for AgentCoordinator multi-agent graph and mailbox messaging."""

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

    # Send message from root to child
    delivered = await coord.send("child01", {
        "from": "root01",
        "content": "Focus on /api/v1/auth/jwt",
        "type": "instruction",
    })
    assert delivered is True

    # Child consumes pending messages
    count, _ = await coord.consume_pending("child01")
    assert count == 1

    # Further consumption returns 0
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
