"""Live Docker integration tests (marked `docker`, skipped when no daemon).

These spin up a real sandbox container. To run:

    docker build -t rakshakx/sandbox:latest -f containers/Dockerfile .
    pytest tests/docker/test_sandbox_live.py -m docker -v
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from rakshak.runtime.docker_client import DockerSandboxClient
from rakshak.tools.output_store import configure_spill_writer

pytestmark = pytest.mark.docker


def _docker_running() -> bool:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_running(),
    reason="Docker daemon not available",
)


@pytest.fixture(scope="module")
def sandbox():
    client = DockerSandboxClient()
    name = f"rakshak-test-{uuid.uuid4().hex[:8]}"
    container = client.create_sandbox(
        image="rakshakx/sandbox:latest",
        name=name,
    )
    yield client, container
    client.stop_and_remove(container.id)


def test_container_running(sandbox):
    _, container = sandbox
    container.reload()
    assert container.status == "running"


def test_exec_command(sandbox):
    client, container = sandbox
    code, out = client.exec_command(container, "echo rakshak-live-test")
    assert code == 0
    assert "rakshak-live-test" in out


def test_nmap_executes_and_sudo_syn_scan(sandbox):
    """Regression: nmap must execute and raw scans must work via sudo.

    The image used to ship file capabilities on the nmap binary, which made
    every exec fail with "Operation not permitted" — even as root. Raw scans
    now run via passwordless sudo (container gets NET_RAW via cap_add).
    """
    client, container = sandbox
    code, out = client.exec_command(container, "nmap --version")
    assert code == 0, out
    assert "Nmap version" in out
    assert "Operation not permitted" not in out

    code, out = client.exec_command(
        container, "sudo -n nmap -sS --top-ports 1 --host-timeout 30s 127.0.0.1"
    )
    assert "Operation not permitted" not in out
    assert code == 0, out


def test_write_and_read_file(sandbox):
    client, container = sandbox
    path = "/workspace/live_write_test.txt"
    client.write_file(container, path, "live content")
    assert client.read_file(container, path) == "live content"


def test_spill_writer_writes_to_sandbox(sandbox):
    _, container = sandbox

    async def writer(output_id: str, text: str):
        client = DockerSandboxClient()
        client.write_file(container, f"/workspace/.rakshak/spill/{output_id}.txt", text)
        return f"/workspace/.rakshak/spill/{output_id}.txt"

    configure_spill_writer(writer)
    try:
        path = asyncio.run(writer("test_x", "spill data"))
        assert ".rakshak/spill" in path
    finally:
        configure_spill_writer(None)
