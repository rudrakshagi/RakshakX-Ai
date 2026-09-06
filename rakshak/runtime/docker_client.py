"""Docker sandbox container management and process execution client."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import tarfile
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container

logger = logging.getLogger(__name__)


class DockerSandboxClient:
    """Manages isolated Docker container lifecycles and exec streams for pentesting."""

    def __init__(self) -> None:
        try:
            self._client = docker.from_env()
            self._client.ping()
        except DockerException as exc:
            raise RuntimeError(
                f"Cannot connect to Docker daemon. Ensure Docker is running. Error: {exc}"
            ) from exc

    def ensure_image(self, image_name: str) -> None:
        """Check if image exists locally; if not, pull it from registry."""
        try:
            self._client.images.get(image_name)
            logger.info("Found local sandbox image: %s", image_name)
        except ImageNotFound:
            logger.info("Sandbox image %s not found locally. Pulling...", image_name)
            self._client.images.pull(image_name)
            logger.info("Successfully pulled sandbox image: %s", image_name)

    def create_sandbox(
        self,
        *,
        image: str,
        name: str,
        bind_mounts: list[dict[str, Any]] | None = None,
        environment: dict[str, str] | None = None,
        ports: dict[str, int | tuple[str, int]] | None = None,
    ) -> Container:
        """Create and start a Kali sandbox container with configured mounts and proxy ports."""
        self.ensure_image(image)

        volumes: dict[str, dict[str, str]] = {}
        for mount in bind_mounts or []:
            src = str(Path(mount["source"]).resolve())
            target = mount["target"]
            mode = "ro" if mount.get("read_only", False) else "rw"
            volumes[src] = {"bind": target, "mode": mode}

        env = dict(environment or {})
        # Map host UID/GID on Linux to avoid file ownership issues
        if os.name != "nt" and hasattr(os, "getuid"):
            env.setdefault("RAKSHAK_HOST_UID", str(os.getuid()))
            env.setdefault("RAKSHAK_HOST_GID", str(os.getgid()))

        container = self._client.containers.create(
            image=image,
            name=name,
            command=["sleep", "infinity"],
            detach=True,
            tty=True,
            stdin_open=True,
            volumes=volumes,
            environment=env,
            ports=ports or {},
            network_mode="bridge",
            # NET_RAW lets nmap run SYN scans (-sS/-sV) and ICMP probes.
            # Without it every nmap run fails with "Operation not permitted"
            # while curl/sqlmap (plain TCP) still work — confusing for agents.
            cap_add=["NET_RAW"],
        )
        container.start()
        # Ensure file capabilities on nmap binary are stripped so execve does not fail with EPERM
        try:
            container.exec_run("setcap -r /usr/lib/nmap/nmap /usr/bin/nmap", user="root")
        except Exception as exc:
            logger.warning("Failed to strip nmap capabilities: %s", exc)
        logger.info("Started sandbox container %s (id=%s)", name, container.short_id)
        return container


    # Default cap so one runaway tool (e.g. a 20-minute ffuf) can never eat
    # a whole scan. GNU `timeout` (coreutils) kills the command and we keep
    # whatever partial output was produced. Pass timeout_s=None/0 to disable.
    DEFAULT_EXEC_TIMEOUT_S = 300.0

    def exec_command(
        self,
        container: Container,
        cmd: str | list[str],
        *,
        workdir: str = "/workspace",
        user: str = "pentester",
        environment: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> tuple[int, str]:
        """Execute a command in the container and return (exit_code, output_text)."""
        if timeout_s is None:
            timeout_s = self.DEFAULT_EXEC_TIMEOUT_S
        cmd_args = ["bash", "-c", cmd] if isinstance(cmd, str) else cmd
        if timeout_s and timeout_s > 0:
            cmd_args = ["timeout", str(timeout_s), *cmd_args]

        exec_res = container.exec_run(
            cmd=cmd_args,
            workdir=workdir,
            user=user,
            environment=environment,
            stdout=True,
            stderr=True,
            demux=False,
        )
        output = exec_res.output.decode("utf-8", errors="replace") if exec_res.output else ""
        if exec_res.exit_code == 124 and timeout_s:
            output += (
                f"\n\n[RakshakX] Command timed out after {timeout_s:g}s and was killed — "
                "output above is partial. Re-run narrower (smaller wordlist, "
                "fewer threads/targets) instead of repeating the same command."
            )
        return exec_res.exit_code, output

    def write_file(
        self,
        container: Container,
        dest_path: str,
        content: str | bytes,
    ) -> None:
        """Write content into a specific file inside the container via tar stream."""
        p = Path(dest_path)
        dir_name = str(p.parent)
        file_name = p.name

        # Ensure target directory exists inside container
        self.exec_command(container, f"mkdir -p '{dir_name}'", user="pentester")

        data = content.encode("utf-8") if isinstance(content, str) else content
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tarinfo = tarfile.TarInfo(name=file_name)
            tarinfo.size = len(data)
            tarinfo.mtime = 0
            tarinfo.mode = 0o644
            tar.addfile(tarinfo, io.BytesIO(data))

        tar_stream.seek(0)
        container.put_archive(path=dir_name, data=tar_stream.getvalue())

    def read_file(self, container: Container, file_path: str) -> str:
        """Read text content of a file from within the container."""
        code, out = self.exec_command(container, f"cat '{file_path}'", user="pentester")
        if code != 0:
            raise FileNotFoundError(f"Cannot read file {file_path} in container: {out}")
        return out

    def stop_and_remove(self, container_id_or_name: str) -> None:
        """Stop and remove a container by name or ID gracefully."""
        try:
            container = self._client.containers.get(container_id_or_name)
            container.stop(timeout=5)
            container.remove(force=True)
            logger.info("Removed sandbox container: %s", container_id_or_name)
        except NotFound:
            pass
        except Exception:
            logger.exception("Failed to clean up container %s", container_id_or_name)

    def remove_container_by_name(self, name: str) -> bool:
        """Remove a (possibly stale) container by exact name. True if one existed.

        Used by the leak reaper and pre-create cleanup: a leftover
        ``rakshak-<scan_id>`` container from a dead backend would otherwise
        make the next ``create`` fail with a name Conflict.
        """
        try:
            container = self._client.containers.get(name)
        except NotFound:
            return False
        except Exception:
            logger.warning("Could not inspect container %s for removal.", name)
            return False
        with contextlib.suppress(Exception):
            container.stop(timeout=5)
        with contextlib.suppress(Exception):
            container.remove(force=True)
        logger.info("Removed stale container %s.", name)
        return True
