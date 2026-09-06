"""Sidecar supervisor + backend log rotation for the viewer server.

Why this exists: the platform is three processes (backend :8080, bridge
:8787, UI :3000) but only the backend is observed. When bridge/vite died
between sessions, chat and UI silently broke until a manual restart — and
each manual restart created yet another `*-relaunch*.log` file while
``/api/logs`` kept reading the stale canonical names.

- :func:`setup_backend_log_rotation` — RotatingFileHandler on the root
  logger (``logs/backend.log``, 2MB x 3). Idempotent.
- :func:`ensure_sidecars` — pure-ish check+restart step over a sidecar
  table; restarts append to the CANONICAL log files the logs API reads.
  Disabled with ``RAKSHAK_SUPERVISE_SIDECARS=0``. Never raises.
- :func:`supervise_forever` — daemon-thread loop around it (30s interval,
  60s per-service restart cooldown).
"""

from __future__ import annotations

import contextlib
import http.client
import logging
import os
import subprocess
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = ROOT_DIR / "logs"

SUPERVISE_ENV = "RAKSHAK_SUPERVISE_SIDECARS"
CHECK_INTERVAL_S = 30.0
RESTART_COOLDOWN_S = 60.0
PROBE_TIMEOUT_S = 3.0

BACKEND_LOG = "backend.log"
BACKEND_LOG_MAX_BYTES = 2 * 1024 * 1024
BACKEND_LOG_BACKUPS = 3

SIDECARS: tuple[dict[str, Any], ...] = (
    {
        # NOTE: single-service commands ONLY. Never `npm run dev` in web/
        # (it is a concurrently TRIO that spawns duplicate backends fighting
        # over :8080) — hence the absolute vite binary, and bare node here.
        "name": "bridge",
        "port": 8787,
        "probe_path": "/v1/models",
        "cwd": "opencode-bridge",
        "cmd": ("node", "server.js"),
        "log": "bridge.log",
    },
    {
        "name": "ui",
        "port": 3000,
        "probe_path": "/",
        "cwd": "web",
        "cmd": ("node_modules/.bin/vite", "--host", "--port", "3000"),
        "log": "frontend.log",
    },
)


def setup_backend_log_rotation(
    logs_dir: Path | None = None,
    max_bytes: int = BACKEND_LOG_MAX_BYTES,
    backups: int = BACKEND_LOG_BACKUPS,
) -> Path | None:
    """Attach a RotatingFileHandler (logs/backend.log) to the root logger.

    Idempotent: repeated calls (dev reloads, tests) never stack handlers.
    Returns the log path, or None if the directory is not writable.
    """
    target_dir = Path(logs_dir) if logs_dir is not None else LOGS_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.warning("Cannot create logs dir %s; skipping file rotation.", target_dir)
        return None
    log_path = target_dir / BACKEND_LOG
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "_rakshak_managed", False):
            return log_path
    try:
        handler = RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
        )
        handler._rakshak_managed = True  # type: ignore[attr-defined]
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root.addHandler(handler)
    except Exception:
        logger.warning("Cannot attach rotating log file %s; continuing on stderr.", log_path, exc_info=True)
        return None
    return log_path


def is_sidecar_up(port: int, probe_path: str = "/", timeout: float = PROBE_TIMEOUT_S) -> bool:
    """True if the sidecar answers HTTP on localhost:port (any status counts)."""
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        conn.request("GET", probe_path)
        res = conn.getresponse()
        conn.close()
        return 100 <= res.status < 600
    except Exception:
        return False


def ensure_sidecars(
    sidecars: tuple[dict[str, Any], ...] = SIDECARS,
    *,
    now: float | None = None,
    last_restart: dict[str, float] | None = None,
    launcher: Any | None = None,
    confirm_delay: float = 3.0,
) -> list[str]:
    """Check each sidecar; restart missing ones (subject to cooldown).

    Returns human-readable event lines (also logged). ``last_restart`` maps
    service name -> epoch of last restart attempt and is updated in place.
    ``launcher`` injects process spawning in tests (defaults to detached Popen).
    Never raises — supervision must not break the backend.
    """
    events: list[str] = []
    if os.environ.get(SUPERVISE_ENV, "1") == "0":
        return events
    at = time.time() if now is None else now
    restarts = last_restart if last_restart is not None else {}

    for spec in sidecars:
        name = str(spec["name"])
        try:
            if is_sidecar_up(int(spec["port"]), str(spec.get("probe_path", "/"))):
                continue
            # Confirm-down: a single failed probe can be a transient blip
            # (slow boot, GC pause). A duplicate spawned on a flake crashes
            # with EADDRINUSE and litters the log — verify twice.
            time.sleep(confirm_delay)
            if is_sidecar_up(int(spec["port"]), str(spec.get("probe_path", "/"))):
                continue
        except Exception:
            logger.debug("Sidecar probe failed for %s; treating as down.", name)
        last = restarts.get(name, 0.0)
        if at - last < RESTART_COOLDOWN_S:
            continue
        try:
            cwd = ROOT_DIR / str(spec["cwd"])
            log_path = LOGS_DIR / str(spec["log"])
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8", errors="replace")  # noqa: PTH123
            try:
                if launcher is not None:
                    launcher(list(spec["cmd"]), cwd, log_file)
                else:
                    subprocess.Popen(  # noqa: S603 — fixed platform commands only
                        list(spec["cmd"]),
                        cwd=str(cwd),
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )
            finally:
                # Popen dups the fd; closing ours is safe and avoids leaks.
                # (Test launchers that only record args are unaffected.)
                with contextlib.suppress(Exception):
                    log_file.close()
            restarts[name] = at
            msg = f"Sidecar '{name}' was down; restarted (logs: {log_path})."
            logger.warning(msg)
            events.append(msg)
        except Exception as exc:
            msg = f"Sidecar '{name}' is down and restart failed: {exc}"
            logger.error(msg)
            events.append(msg)
    return events


def supervise_forever(interval: float = CHECK_INTERVAL_S) -> None:
    """Daemon-thread entrypoint: heal missing sidecars until process exit."""
    restarts: dict[str, float] = {}
    while True:
        try:
            ensure_sidecars(last_restart=restarts)
        except Exception:
            logger.debug("Supervisor tick failed; continuing.", exc_info=True)
        time.sleep(interval)


def start_supervisor_thread() -> threading.Thread:
    """Launch the supervisor daemon thread (idempotent per call)."""
    thread = threading.Thread(target=supervise_forever, name="rakshak-sidecar-supervisor", daemon=True)
    thread.start()
    return thread
