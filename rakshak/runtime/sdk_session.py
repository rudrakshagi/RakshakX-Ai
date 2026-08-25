"""SDK-compatible `BaseSandboxSession` adapter backed by the RakshakX Docker sandbox.

The openai-agents SDK requires sandbox sessions passed through `SandboxRunConfig` to
implement its own `BaseSandboxSession` protocol. RakshakX manages containers directly
via `docker`, so this adapter bridges the two while preserving the container lifecycle
orchestration in `rakshak.runtime.session_manager`.
"""

from __future__ import annotations

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

from rakshak.runtime.docker_client import DockerSandboxClient

logger = logging.getLogger(__name__)


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
            self._container.reload()
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
        _ = timeout
        exit_code, merged = self._docker_client.exec_command(
            self._container,
            [str(c) for c in command],
            workdir=self._workspace_root,
        )
        MAX_OUTPUT_CHARS = 4_000
        if len(merged) > MAX_OUTPUT_CHARS:
            merged = (
                merged[:MAX_OUTPUT_CHARS]
                + "\n\n[output truncated by RakshakX: exceeded 4k chars]"
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
