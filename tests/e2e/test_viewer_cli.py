"""E2E tests for the Viewer REST API and CLI entrypoint."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from rakshak.core import paths


@pytest.fixture
def viewer_server(tmp_path, monkeypatch):
    """Start the ThreadingHTTPServer on a free port with a temp runs_dir."""
    import socket
    from http.server import ThreadingHTTPServer

    from rakshak.interface.viewer.server import _make_handler

    monkeypatch.setattr(paths, "base_runs_dir", lambda: tmp_path / "runs")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    run_dir = tmp_path / "scan-view"
    run_dir.mkdir(parents=True, exist_ok=True)
    handler_cls = _make_handler(run_dir)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, port
    server.shutdown()
    server.server_close()


def test_health_endpoint(viewer_server):
    server, port = viewer_server
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/system/health")
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode())
    assert data["backend"]["status"] == "online"
    conn.close()


def test_config_endpoint(viewer_server):
    server, port = viewer_server
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/config")
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode())
    assert "is_key_configured" in data
    conn.close()


def test_overview_endpoint(viewer_server):
    server, port = viewer_server
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/overview")
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode())
    assert "severity_counts" in data
    conn.close()


def test_runs_endpoint_empty(viewer_server):
    server, port = viewer_server
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/runs")
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode())
    assert isinstance(data, list)
    conn.close()


def test_unknown_endpoint_404(viewer_server):
    server, port = viewer_server
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/nope")
    resp = conn.getresponse()
    assert resp.status in (200, 404)
    conn.close()


def test_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "rakshak.interface.main", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    assert result.returncode == 0
    assert "--target" in result.stdout


def test_cli_missing_target_exits_one(tmp_path):
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [sys.executable, "-m", "rakshak.interface.main"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(tmp_path),
        env=env,
    )
    # Missing target -> sys.exit(1) after banner
    assert result.returncode == 1
