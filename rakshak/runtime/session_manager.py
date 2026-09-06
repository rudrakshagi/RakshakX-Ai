"""Sandbox session lifecycle and per-scan container orchestration."""

from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docker.errors import APIError
from docker.models.containers import Container

from rakshak.config.settings import load_settings
from rakshak.runtime.caido_bootstrap import bootstrap_caido
from rakshak.runtime.docker_client import DockerSandboxClient
from rakshak.runtime.sdk_session import SDKSandboxSession

logger = logging.getLogger(__name__)

StatusSink = Callable[[str], None]
# In-container ports: the intercept proxy (tool + http_proxy traffic) and the
# UI/GraphQL API (bootstrap polling) are separate caido-cli listeners.
_CONTAINER_CAIDO_PROXY_PORT = 48080
_CONTAINER_CAIDO_API_PORT = 48082
_SESSION_CACHE: dict[str, SandboxSessionBundle] = {}

# docker APIError text markers for host-port bind collisions. _find_free_port
# has a close-then-bind race (TOCTOU): another process can grab the port
# before the container binds it, so create must retry with fresh ports.
_PORT_CONFLICT_MARKERS = (
    "port is already allocated",
    "address already in use",
    "failed to bind",
    "bind for",
)
_CREATE_MAX_ATTEMPTS = 3


def _find_free_port() -> int:
    """Find an available ephemeral port on the host machine."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(s.getsockname()[1])


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
        timeout_s: float | None = None,
    ) -> tuple[int, str]:
        """Execute a shell command inside the sandbox."""
        # exec_command blocks the calling thread (up to timeout_s) — same
        # Phase-1 rule as sdk_session: never run it on the event loop.
        return await asyncio.to_thread(
            self.docker_client.exec_command,
            self.container,
            command,
            workdir=workdir,
            user=user,
            environment=environment,
            timeout_s=timeout_s,
        )

    async def write(self, path: str | Path, content: str | bytes) -> None:
        """Write content to a file inside the sandbox."""
        await asyncio.to_thread(
            self.docker_client.write_file, self.container, str(path), content
        )

    async def read(self, path: str | Path) -> str:
        """Read text from a file inside the sandbox."""
        return await asyncio.to_thread(
            self.docker_client.read_file, self.container, str(path)
        )


@dataclass(slots=True)
class SandboxSessionBundle:
    """Bundle containing the active session, docker client, container, and proxy client."""
    scan_id: str
    session: SandboxSession
    sdk_session: SDKSandboxSession
    container: Container
    caido_client: Any | None
    host_proxy_port: int | None
    host_api_port: int | None = None


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

    # Allocate host ports for the Caido proxy AND the UI/GraphQL API
    # (separate in-container listeners; bootstrap polls the API port).
    container_name = f"rakshak-{scan_id}"

    # A leftover container with the same name (dead backend, killed scan)
    # would make create fail with Conflict — clear it first. In-cache
    # bundles returned above, so anything here is genuinely stale.
    if docker_client.remove_container_by_name(container_name):
        report(f"Removed stale container '{container_name}' from a previous run...")
        logger.warning("Pre-create cleanup removed stale %s.", container_name)

    container = None
    for attempt in range(1, _CREATE_MAX_ATTEMPTS + 1):
        host_proxy_port = _find_free_port() if settings.runtime.enable_caido else None
        host_api_port = _find_free_port() if settings.runtime.enable_caido else None
        ports_map: dict[str, int | tuple[str, int]] = {}
        if host_proxy_port is not None and host_api_port is not None:
            ports_map = {
                f"{_CONTAINER_CAIDO_PROXY_PORT}/tcp": host_proxy_port,
                f"{_CONTAINER_CAIDO_API_PORT}/tcp": host_api_port,
            }

        report(f"Creating isolated sandbox container '{container_name}'...")
        try:
            container = docker_client.create_sandbox(
                image=resolved_image,
                name=container_name,
                bind_mounts=bind_mounts,
                ports=ports_map,
            )
            break
        except APIError as exc:
            err_text = str(exc).lower()
            is_port_conflict = any(m in err_text for m in _PORT_CONFLICT_MARKERS)
            if is_port_conflict and attempt < _CREATE_MAX_ATTEMPTS:
                logger.warning(
                    "Host port collision creating %s (attempt %d/%d); re-picking ports...",
                    container_name, attempt, _CREATE_MAX_ATTEMPTS,
                )
                continue
            raise
    if container is None:
        raise RuntimeError(
            f"Failed to create sandbox container {container_name!r} after "
            f"{_CREATE_MAX_ATTEMPTS} attempts (persistent port collision)."
        )

    session = SandboxSession(container=container, docker_client=docker_client)

    sdk_session = SDKSandboxSession(
        container=container,
        docker_client=docker_client,
    )

    # Ingest extra seed files into workspace
    for extra in extra_files or []:
        rel_path = extra.get("workspace_path", "").removeprefix("/workspace/").removeprefix("/")
        content = extra.get("content", "")
        if rel_path and content:
            await session.write(f"/workspace/{rel_path}", content)

    # Bootstrap Caido proxy client if enabled (via the UI/API port mapping)
    caido_client = None
    if host_api_port is not None and settings.runtime.enable_caido:
        report("Bootstrapping Caido proxy sidecar...")
        try:
            caido_client = await bootstrap_caido(host_api_port, project_name=scan_id)
        except Exception:
            logger.warning("Could not bootstrap Caido client; proceeding with direct scanning.")

    bundle = SandboxSessionBundle(
        scan_id=scan_id,
        session=session,
        sdk_session=sdk_session,
        container=container,
        caido_client=caido_client,
        host_proxy_port=host_proxy_port,
        host_api_port=host_api_port,
    )
    _SESSION_CACHE[scan_id] = bundle
    return bundle


async def cleanup(scan_id: str) -> None:
    """Tear down and remove the sandbox container for a scan."""
    bundle = _SESSION_CACHE.pop(scan_id, None)
    if bundle is not None:
        logger.info("Cleaning up sandbox container for scan %s", scan_id)
        bundle.session.docker_client.stop_and_remove(bundle.container.id)
