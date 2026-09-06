"""E2E tests for the agentic chat loop (steer queue + MCP offline path).

Covers:
  (a) POST /api/steer with target_agent_id round-trips via GET /api/steer.
      Prefers a live backend at localhost:8080 when reachable; otherwise spins
      an ephemeral in-process viewer handler (no external server management).
  (b) poll_steer_queue dedupe: second poll with the returned index yields nothing new.
  (c) MCP handle_tool_call offline path returns queued_offline when the backend
      URL points at a dead port.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest


# ---------------------------------------------------------------------------
# (a) steer round-trip
# ---------------------------------------------------------------------------

def _http_json(method: str, url: str, payload: dict | None = None, timeout: float = 5.0):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_steer_post_with_target_roundtrips_via_get(tmp_path):
    """POST /api/steer with target_agent_id must be visible on GET /api/steer.

    Tests the viewer handler directly via an ephemeral in-process server built
    from current source. NOTE: a live backend on localhost:8080 was observed to
    drop target_agent_id (stale code predating target support), so live is
    deliberately NOT used here — this keeps the test pinned to current source.
    """
    instruction = "e2e-probe-focus-on-jwt"
    target_agent_id = "agent-e2e-1"

    # Ephemeral in-process viewer handler bound to a tmp run dir.
    # NOTE: conftest monkeypatches base_runs_dir; steer handlers resolve via the
    # run_dir captured in _make_handler, so passing tmp_path keeps this hermetic.
    import rakshak.interface.viewer.server as viewer_server

    run_dir = tmp_path / "run-steer-e2e"
    run_dir.mkdir(parents=True, exist_ok=True)
    prev_active = viewer_server._active_scan_dir
    viewer_server._active_scan_dir = None
    handler_cls = viewer_server._make_handler(run_dir)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"
        status, posted = _http_json(
            "POST",
            f"{base}/api/steer",
            {"instruction": instruction, "target_agent_id": target_agent_id},
        )
        assert status == 200
        assert posted.get("success") is True
        _, got = _http_json("GET", f"{base}/api/steer")
        queue = got.get("queue", [])
        assert any(
            q.get("instruction") == instruction and q.get("target_agent_id") == target_agent_id
            for q in queue
        ), f"posted steer entry not found in queue: {queue}"
    finally:
        server.shutdown()
        thread.join(timeout=5.0)
        viewer_server._active_scan_dir = prev_active


# ---------------------------------------------------------------------------
# (b) poll_steer_queue dedupe
# ---------------------------------------------------------------------------

def test_poll_steer_queue_dedupe(tmp_path):
    from rakshak.core.execution import poll_steer_queue

    state_dir = tmp_path / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)
    queue = [
        {"instruction": "check jwt", "timestamp": 1.0, "iso": "2026-01-01T00:00:00+00:00"},
        {"instruction": "check sqli", "timestamp": 2.0, "iso": "2026-01-01T00:00:01+00:00"},
    ]
    (state_dir / "steer_queue.json").write_text(json.dumps(queue), encoding="utf-8")

    first_items, next_index = poll_steer_queue(state_dir, 0)
    assert len(first_items) == 2
    assert next_index == 2

    # Second poll from the returned index must yield no new items (dedupe).
    second_items, second_index = poll_steer_queue(state_dir, next_index)
    assert second_items == []
    assert second_index == next_index


# ---------------------------------------------------------------------------
# (c) MCP offline path
# ---------------------------------------------------------------------------

def test_mcp_handle_tool_call_offline_queued(monkeypatch):
    from rakshak.mcp.server import handle_tool_call

    # Dead port: nothing listens on 9 (discard); connection refused/fast-fail.
    monkeypatch.setenv("RAKSHAK_BACKEND_URL", "http://127.0.0.1:9")
    result = handle_tool_call(
        "rakshak_start_scan", {"target": "example.com", "mode": "blackbox"}
    )
    assert result.get("status") == "queued_offline", f"got: {result}"
    assert result.get("target") == "example.com"
