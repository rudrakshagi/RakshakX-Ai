"""Unit tests for Phase-4 observability harness (no real servers/containers).

Covers:
- ``rakshak.interface.viewer.supervisor.setup_backend_log_rotation``:
  creation, idempotency (no duplicate handlers), write-through, rollover.
- ``supervisor.is_sidecar_up``: closed port False, live localhost HTTP True.
- ``supervisor.ensure_sidecars``: restart down service via injected launcher,
  60s cooldown, kill-switch, launcher-failure containment.
- ``rakshak.interface.viewer.server._mark_agents_terminal``: terminal marking,
  missing/corrupt file tolerance.
- ``/api/logs`` ``?scan=`` filter: response-shape contract via code
  inspection (the filter is inline in the handler, not factored into an
  importable helper; no live HTTP per minimal-diff rule).

All I/O is to tmp dirs / loopback; no docker, no real sidecars.
"""

from __future__ import annotations

import inspect
import json
import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from rakshak.core.paths import runtime_state_dir
from rakshak.interface.viewer import supervisor
from rakshak.interface.viewer.server import _mark_agents_terminal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _managed_handlers() -> list[RotatingFileHandler]:
    root = logging.getLogger()
    return [
        h for h in root.handlers
        if isinstance(h, RotatingFileHandler) and getattr(h, "_rakshak_managed", False)
    ]


def _remove_managed_handlers() -> None:
    root = logging.getLogger()
    for h in _managed_handlers():
        with __import__("contextlib").suppress(Exception):
            root.removeHandler(h)
        with __import__("contextlib").suppress(Exception):
            h.close()


@pytest.fixture(autouse=True)
def _isolate_rotation_handlers():
    """Start/end each test with zero managed handlers so logging is unaffected."""
    _remove_managed_handlers()
    yield
    _remove_managed_handlers()


def _free_closed_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _OKHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def live_http_server():
    """Real loopback HTTP server on an ephemeral port (fast, flake-free)."""
    srv = HTTPServer(("127.0.0.1", 0), _OKHandler)
    srv.timeout = 0.5
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield port
    srv.shutdown()
    thread.join(timeout=5)
    srv.server_close()


def _fake_run_dir(base: Path, agents: dict | None) -> Path:
    run_dir = base / "scan-test123"
    state_dir = runtime_state_dir(run_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    if agents is not None:
        (state_dir / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
    return run_dir


# ---------------------------------------------------------------------------
# 1. Log rotation
# ---------------------------------------------------------------------------

def test_rotation_creates_idempotent_and_writes(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    before = len(_managed_handlers())

    path = supervisor.setup_backend_log_rotation(logs_dir, max_bytes=1_000_000, backups=3)
    assert path == logs_dir / "backend.log"
    assert path.exists()
    assert len(_managed_handlers()) == before + 1

    # Second call adds NO duplicate handler (idempotent via _rakshak_managed).
    path2 = supervisor.setup_backend_log_rotation(logs_dir, max_bytes=1_000_000, backups=3)
    assert path2 == logs_dir / "backend.log"
    assert len(_managed_handlers()) == before + 1

    # Write-through: a log record lands in backend.log.
    logging.getLogger("rakshak-test-rotation").warning("rotation-probe-marker-abc123")
    for h in _managed_handlers():
        h.flush()
    assert "rotation-probe-marker-abc123" in path.read_text(encoding="utf-8")


def test_rotation_rollover_on_overflow(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    path = supervisor.setup_backend_log_rotation(logs_dir, max_bytes=200, backups=1)
    assert path is not None
    handler = _managed_handlers()[0]
    assert handler.backupCount == 1

    # Overflow the tiny budget so RotatingFileHandler rolls to backend.log.1.
    for i in range(30):
        logging.getLogger("rakshak-test-rotation").warning("overflow-line-%02d %s", i, "x" * 120)
    for h in _managed_handlers():
        h.flush()

    rolled = logs_dir / "backend.log.1"
    assert rolled.exists(), "expected backend.log.1 after exceeding tiny max_bytes"


# ---------------------------------------------------------------------------
# 2. is_sidecar_up
# ---------------------------------------------------------------------------

def test_is_sidecar_up_closed_port_is_false() -> None:
    assert supervisor.is_sidecar_up(_free_closed_port(), "/", timeout=1.0) is False


def test_is_sidecar_up_live_server_is_true(live_http_server: int) -> None:
    assert supervisor.is_sidecar_up(live_http_server, "/", timeout=2.0) is True


# ---------------------------------------------------------------------------
# 3. ensure_sidecars
# ---------------------------------------------------------------------------

def _sidecar_table(down_port: int, up_port: int) -> tuple[dict, ...]:
    return (
        {"name": "down-svc", "port": down_port, "probe_path": "/",
         "cwd": "fake-down", "cmd": ("echo", "down"), "log": "down.log"},
        {"name": "up-svc", "port": up_port, "probe_path": "/",
         "cwd": "fake-up", "cmd": ("echo", "up"), "log": "up.log"},
    )


def test_ensure_sidecars_restart_cooldown_and_relaunch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, live_http_server: int
) -> None:
    monkeypatch.setattr(supervisor, "ROOT_DIR", tmp_path / "root")
    monkeypatch.setattr(supervisor, "LOGS_DIR", tmp_path / "logs")
    down_port = _free_closed_port()
    table = _sidecar_table(down_port, live_http_server)

    calls: list[tuple[list[str], object, object]] = []

    def launcher(cmd: list[str], cwd: object, logfile: object) -> None:
        calls.append((cmd, cwd, logfile))

    now = 1_000_000.0
    last_restart: dict[str, float] = {}
    events = supervisor.ensure_sidecars(table, now=now, last_restart=last_restart, launcher=launcher)

    # Down service launched exactly once; up service untouched.
    assert len(calls) == 1
    cmd, cwd, logfile = calls[0]
    assert cmd == ["echo", "down"]
    assert str(cwd) == str(tmp_path / "root" / "fake-down")
    assert getattr(logfile, "name", "").endswith("down.log")
    assert str(tmp_path / "logs") in str(getattr(logfile, "name", ""))
    assert last_restart.get("down-svc") == now
    assert "up-svc" not in last_restart
    assert len(events) == 1 and "down-svc" in events[0]

    # Immediate second tick: cooldown suppresses relaunch.
    events2 = supervisor.ensure_sidecars(table, now=now + 10, last_restart=last_restart, launcher=launcher)
    assert len(calls) == 1
    assert events2 == []

    # After cooldown (+70s): relaunches.
    events3 = supervisor.ensure_sidecars(table, now=now + 70, last_restart=last_restart, launcher=launcher)
    assert len(calls) == 2
    assert last_restart["down-svc"] == now + 70
    assert len(events3) == 1


def test_ensure_sidecars_kill_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, live_http_server: int
) -> None:
    monkeypatch.setattr(supervisor, "ROOT_DIR", tmp_path / "root")
    monkeypatch.setattr(supervisor, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setenv(supervisor.SUPERVISE_ENV, "0")
    table = _sidecar_table(_free_closed_port(), live_http_server)

    launched: list = []
    events = supervisor.ensure_sidecars(
        table, now=2_000_000.0, last_restart={},
        launcher=lambda *a: launched.append(a),
    )
    assert launched == []
    assert events == []


def test_ensure_sidecars_launcher_failure_contained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(supervisor, "ROOT_DIR", tmp_path / "root")
    monkeypatch.setattr(supervisor, "LOGS_DIR", tmp_path / "logs")
    table = _sidecar_table(_free_closed_port(), _free_closed_port())

    def boom(cmd: list[str], cwd: object, logfile: object) -> None:
        raise RuntimeError("spawn exploded")

    events = supervisor.ensure_sidecars(table, now=3_000_000.0, last_restart={}, launcher=boom)
    # No exception propagates; failure recorded as an event line.
    assert len(events) == 2
    assert all("restart failed" in e for e in events)


# ---------------------------------------------------------------------------
# 4. _mark_agents_terminal
# ---------------------------------------------------------------------------

def test_mark_agents_terminal_transitions_only_non_terminal(tmp_path: Path) -> None:
    agents = {
        "names": {"a": "Recon", "b": "SQLi", "c": "JWT", "d": "SSRF", "e": "RCE"},
        "statuses": {"a": "running", "b": "waiting", "c": "completed", "d": "failed", "e": ""},
        "metadata": {},
    }
    run_dir = _fake_run_dir(tmp_path, agents)
    _mark_agents_terminal(run_dir, "completed")

    out = json.loads((runtime_state_dir(run_dir) / "agents.json").read_text(encoding="utf-8"))
    assert out["statuses"]["a"] == "completed"
    assert out["statuses"]["b"] == "completed"
    assert out["statuses"]["e"] == "completed"  # "" counts as non-terminal
    assert out["statuses"]["c"] == "completed"  # already terminal, untouched value
    assert out["statuses"]["d"] == "failed"  # already terminal, untouched value

    # Failed-terminal variant on a fresh dir.
    run_dir2 = _fake_run_dir(tmp_path / "second", agents)
    _mark_agents_terminal(run_dir2, "failed")
    out2 = json.loads((runtime_state_dir(run_dir2) / "agents.json").read_text(encoding="utf-8"))
    assert out2["statuses"]["a"] == "failed"
    assert out2["statuses"]["b"] == "failed"
    assert out2["statuses"]["d"] == "failed"


def test_mark_agents_terminal_missing_file_no_raise(tmp_path: Path) -> None:
    run_dir = tmp_path / "scan-missing"
    run_dir.mkdir(parents=True, exist_ok=True)
    _mark_agents_terminal(run_dir, "completed")  # must not raise


def test_mark_agents_terminal_corrupt_json_no_raise(tmp_path: Path) -> None:
    run_dir = tmp_path / "scan-corrupt"
    state_dir = runtime_state_dir(run_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "agents.json").write_text("{not valid json!!!", encoding="utf-8")
    _mark_agents_terminal(run_dir, "failed")  # must not raise


# ---------------------------------------------------------------------------
# 5. /api/logs ?scan= filter — response-shape contract (no live HTTP)
# ---------------------------------------------------------------------------

def test_api_logs_scan_filter_contract() -> None:
    """The ?scan= filter is inline in the handler (not an importable helper).

    This pins the response-shape contract by inspection so a refactor that
    drops the substring filter or the echoed ``"scan"`` key fails loudly.
    Live-HTTP coverage is deliberately skipped (server binds ports, needs
    run dirs); see tests/e2e/test_viewer_cli.py for live handler tests.
    """
    src = inspect.getsource(__import__("rakshak.interface.viewer.server", fromlist=["x"]))
    assert 'query.get("scan")' in src, "handler must read the ?scan= query param"
    assert "scan_filter in (e.get(\"raw\")" in src, "handler must substring-filter on raw line"
    assert '"scan": scan_filter or None' in src, "handler must echo scan in response JSON"
