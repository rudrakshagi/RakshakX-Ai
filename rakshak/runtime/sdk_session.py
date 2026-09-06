"""SDK-compatible `BaseSandboxSession` adapter backed by the RakshakX Docker sandbox.

The openai-agents SDK requires sandbox sessions passed through `SandboxRunConfig` to
implement its own `BaseSandboxSession` protocol. RakshakX manages containers directly
via `docker`, so this adapter bridges the two while preserving the container lifecycle
orchestration in `rakshak.runtime.session_manager`.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
from pathlib import Path
from typing import Any, Literal

from agents.sandbox.manifest import Manifest
from agents.sandbox.session.base_sandbox_session import BaseSandboxSession
from agents.sandbox.session.sandbox_session_state import SandboxSessionState
from agents.sandbox.snapshot import SnapshotBase
from agents.sandbox.types import ExecResult, User
from docker.models.containers import Container

from rakshak.core.agents import current_heartbeat_scope
from rakshak.runtime.docker_client import DockerSandboxClient
from rakshak.tools.output_store import bound_and_store

logger = logging.getLogger(__name__)

# Model-facing budget for a single exec result (~4k chars, head+tail window).
# Preserves the pre-Phase-3 "exceeded 4k chars" threshold: bounded output goes
# to the model while the FULL text still spills to the sandbox spill file
# (path referenced in the header) when a writer is bound, so nothing is lost.
_EXEC_MAX_LINES = 100
_EXEC_MAX_BYTES = 4_000
_EXEC_MAX_TOKENS = 1_500


class _NoopSnapshot(SnapshotBase):
    """Snapshot implementation that never persists data (container-managed workspace)."""

    type: Literal["rakshakx"] = "rakshakx"

    async def persist(
        self, data: io.IOBase, *, dependencies: Any | None = None
    ) -> None:
        _ = (data, dependencies)

    async def restore(self, *, dependencies: Any | None = None) -> io.IOBase:
        _ = dependencies
        return io.BytesIO()

    async def restorable(self, *, dependencies: Any | None = None) -> bool:
        _ = dependencies
        return False


class SDKSandboxSession(BaseSandboxSession):
    """Adapts a running RakshakX Docker container to the agents SDK sandbox interface."""

    def __init__(
        self,
        *,
        container: Container,
        docker_client: DockerSandboxClient,
        workspace_root: str = "/workspace",
    ) -> None:
        self._container = container
        self._docker_client = docker_client
        self._workspace_root = workspace_root
        self.state = SandboxSessionState(
            type="rakshakx",
            snapshot=_NoopSnapshot(id="container"),
            manifest=Manifest(root=workspace_root),
            workspace_root_ready=True,
        )

    async def running(self) -> bool:
        try:
            # container.reload() is blocking HTTP — never run it on the
            # event loop or the heartbeat ticker starves.
            await asyncio.to_thread(self._container.reload)
            return bool(self._container.status == "running")
        except Exception:
            logger.warning("Failed to inspect container status", exc_info=True)
            return False

    async def start(self) -> None:
        self.state.workspace_root_ready = True

    async def shutdown(self) -> None:
        return

    async def _exec_internal(
        self,
        *command: str | Path,
        timeout: float | None = None,
    ) -> ExecResult:
        # The SDK passes a timeout but it was previously ignored (`_ = timeout`),
        # letting one tool hang a scan forever. Honor it, defaulting to the
        # client cap (300s) when the SDK expresses no preference.
        if timeout is None or timeout <= 0:
            timeout = DockerSandboxClient.DEFAULT_EXEC_TIMEOUT_S
        # Publish the command to the watchdog BEFORE blocking: the UI shows
        # what the agent is executing, not just "executing_tool".
        scope = current_heartbeat_scope()
        if scope is not None:
            coordinator, agent_id = scope
            short_cmd = " ".join(" ".join(str(c) for c in command).split())[:120]
            with contextlib.suppress(Exception):
                await coordinator.touch_heartbeat(
                    agent_id, phase="executing_tool", exec_detail=short_cmd
                )
        # container.exec_run() blocks the calling thread for the whole
        # command duration (up to timeout_s). It MUST run in a worker thread:
        # on the event loop it freezes the 3s heartbeat ticker and the UI
        # watchdog falsely declares the agent stuck.
        exit_code, merged = await asyncio.to_thread(
            self._docker_client.exec_command,
            self._container,
            [str(c) for c in command],
            workdir=self._workspace_root,
            timeout_s=timeout,
        )
        # Oversized output: head+tail window to the model, FULL text spilled
        # to the sandbox spill file (path referenced in the header) so the
        # agent can grep slices on demand. Nothing is silently lost.
        merged = await bound_and_store(
            merged,
            max_lines=_EXEC_MAX_LINES,
            max_bytes=_EXEC_MAX_BYTES,
            max_tokens=_EXEC_MAX_TOKENS,
        )
        stdout = merged.encode("utf-8", errors="replace")
        return ExecResult(stdout=stdout, stderr=b"", exit_code=exit_code)

    async def read(
        self,
        path: Path,
        *,
        user: str | User | None = None,
    ) -> io.IOBase:
        _ = user
        try:
            text = self._docker_client.read_file(self._container, str(path))
        except FileNotFoundError:
            raise
        return io.BytesIO(text.encode("utf-8", errors="replace"))

    async def write(
        self,
        path: Path,
        data: io.IOBase,
        *,
        user: str | User | None = None,
    ) -> None:
        _ = user
        content = data.read()
        if isinstance(content, str):
            payload: str | bytes = content
        else:
            payload = bytes(content)
        self._docker_client.write_file(self._container, str(path), payload)

    async def persist_workspace(self) -> io.IOBase:
        return io.BytesIO(b"")

    async def hydrate_workspace(self, data: io.IOBase) -> None:
        _ = data
