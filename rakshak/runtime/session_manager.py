"""Sandbox session lifecycle and per-scan container orchestration."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from docker.models.containers import Container
from rakshak.config.settings import load_settings
from rakshak.runtime.caido_bootstrap import bootstrap_caido
from rakshak.runtime.docker_client import DockerSandboxClient

logger = logging.getLogger(__name__)

StatusSink = Callable[[str], None]
_CONTAINER_CAIDO_PORT = 48080
_SESSION_CACHE: dict[str, SandboxSessionBundle] = {}


def _find_free_port() -> int:
    """Find an available ephemeral port on the host machine."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@dataclass(slots=True)
class SandboxSession:
    """High-level handle for executing commands and managing files in the active container."""
    container: Container
    docker_client: DockerSandboxClient

    async def exec(
        self,
        command: str | list[str],
        *,
        workdir: str = "/workspace",
        user: str = "pentester",
        environment: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        """Execute a shell command inside the sandbox."""
        return self.docker_client.exec_command(
            self.container,
            command,
            workdir=workdir,
            user=user,
            environment=environment,
        )

    async def write(self, path: str | Path, content: str | bytes) -> None:
        """Write content to a file inside the sandbox."""
        self.docker_client.write_file(self.container, str(path), content)

    async def read(self, path: str | Path) -> str:
        """Read text from a file inside the sandbox."""
        return self.docker_client.read_file(self.container, str(path))


@dataclass(slots=True)
class SandboxSessionBundle:
    """Bundle containing the active session, docker client, container, and proxy client."""
    scan_id: str
    session: SandboxSession
    container: Container
    caido_client: Any | None
    host_proxy_port: int | None


async def create_or_reuse(
    scan_id: str,
    *,
    image: str | None = None,
    local_sources: list[dict[str, Any]] | None = None,
    extra_files: list[dict[str, Any]] | None = None,
    status_sink: StatusSink | None = None,
) -> SandboxSessionBundle:
    """Instantiate a sandbox container for a scan or reuse an existing one."""
    if scan_id in _SESSION_CACHE:
        return _SESSION_CACHE[scan_id]

    def report(phase: str) -> None:
        if status_sink is not None:
            status_sink(phase)

    settings = load_settings()
    resolved_image = image or settings.runtime.docker_image
    docker_client = DockerSandboxClient()

    report(f"Ensuring sandbox image '{resolved_image}' is available...")
    docker_client.ensure_image(resolved_image)

    # Set up bind mounts for target codebases
    bind_mounts: list[dict[str, Any]] = []
    for src in local_sources or []:
        host_path = src.get("source_path")
        ws_subdir = src.get("workspace_subdir") or "target"
        if host_path and Path(host_path).exists():
            bind_mounts.append({
                "source": str(Path(host_path).resolve()),
                "target": f"/workspace/{ws_subdir}",
                "read_only": False,
            })

    # Allocate host port for Caido proxy
    host_port = _find_free_port() if settings.runtime.enable_caido else None
    ports_map = {f"{_CONTAINER_CAIDO_PORT}/tcp": host_port} if host_port else {}

    container_name = f"rakshak-{scan_id}"
    report(f"Creating isolated sandbox container '{container_name}'...")

    container = docker_client.create_sandbox(
        image=resolved_image,
        name=container_name,
        bind_mounts=bind_mounts,
        ports=ports_map,
    )

    session = SandboxSession(container=container, docker_client=docker_client)

    # Ingest extra seed files into workspace
    for extra in extra_files or []:
        rel_path = extra.get("workspace_path", "").lstrip("/workspace/").lstrip("/")
        content = extra.get("content", "")
        if rel_path and content:
            await session.write(f"/workspace/{rel_path}", content)

    # Bootstrap Caido proxy client if enabled
    caido_client = None
    if host_port is not None and settings.runtime.enable_caido:
        report("Bootstrapping Caido proxy sidecar...")
        try:
            caido_client = await bootstrap_caido(host_port, project_name=scan_id)
        except Exception:
            logger.warning("Could not bootstrap Caido client; proceeding with direct scanning.")

    bundle = SandboxSessionBundle(
        scan_id=scan_id,
        session=session,
        container=container,
        caido_client=caido_client,
        host_proxy_port=host_port,
    )
    _SESSION_CACHE[scan_id] = bundle
    return bundle


async def cleanup(scan_id: str) -> None:
    """Tear down and remove the sandbox container for a scan."""
    bundle = _SESSION_CACHE.pop(scan_id, None)
    if bundle is not None:
        logger.info("Cleaning up sandbox container for scan %s", scan_id)
        bundle.session.docker_client.stop_and_remove(bundle.container.id)
