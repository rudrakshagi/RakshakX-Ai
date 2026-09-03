"""Unit tests for DockerSandboxClient using mocked docker client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rakshak.runtime.docker_client import DockerSandboxClient


def _fake_container():
    c = MagicMock()
    c.short_id = "abc123"
    return c


def test_ensure_image_uses_cache_when_present():
    images = MagicMock()
    images.get.side_effect = lambda name: MagicMock()
    client = MagicMock()
    client.images = images
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    manager.ensure_image("rakshakx/sandbox:latest")
    images.get.assert_called_once_with("rakshakx/sandbox:latest")
    images.pull.assert_not_called()


def test_ensure_image_pulls_when_not_found():
    from docker.errors import ImageNotFound

    images = MagicMock()
    images.get.side_effect = ImageNotFound("missing")
    client = MagicMock()
    client.images = images
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    manager.ensure_image("rakshakx/sandbox:latest")
    images.pull.assert_called_once_with("rakshakx/sandbox:latest")


def test_create_sandbox_volumes_ports_env():
    containers = MagicMock()
    container = _fake_container()
    containers.create.return_value = container
    client = MagicMock()
    client.images.get.return_value = MagicMock()
    client.containers = containers
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    manager.create_sandbox(
        image="rakshakx/sandbox:latest",
        name="rakshak-test",
        bind_mounts=[{"source": "/tmp/src", "target": "/workspace/target"}],
        ports={"48080/tcp": 12345},
    )

    containers.create.assert_called_once()
    kwargs = containers.create.call_args.kwargs
    assert kwargs["name"] == "rakshak-test"
    assert kwargs["ports"] == {"48080/tcp": 12345}
    assert "/tmp/src" in kwargs["volumes"]
    container.start.assert_called_once()


def test_exec_command_runs_bash():
    exec_res = MagicMock()
    exec_res.exit_code = 0
    exec_res.output = b"hello world"
    container = MagicMock()
    container.exec_run.return_value = exec_res
    client = MagicMock()
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    code, out = manager.exec_command(container, "echo hi")
    assert code == 0
    assert "hello" in out


def test_write_file_mkdir_parent(tmp_path):
    """Verify write_file first creates the parent dir via bash, then puts archive."""
    container = MagicMock()
    exec_run = MagicMock(return_value=MagicMock(exit_code=0, output=b""))
    container.exec_run = exec_run
    put_archive = MagicMock()
    container.put_archive = put_archive
    client = MagicMock()
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    dest = "/workspace/.rakshak/spill/out_abc.txt"
    manager.write_file(container, dest, "some content")

    cmd = " ".join(exec_run.call_args.kwargs["cmd"])
    assert "mkdir -p" in cmd
    put_archive.assert_called_once()


def test_read_file_raises_on_nonzero():
    container = MagicMock()
    container.exec_run.return_value = MagicMock(exit_code=1, output=b"missing")
    client = MagicMock()
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    with pytest.raises(FileNotFoundError):
        manager.read_file(container, "/nope/file.txt")


def test_stop_and_remove():
    container = MagicMock()
    containers = MagicMock()
    containers.get.return_value = container
    client = MagicMock()
    client.containers = containers
    manager = DockerSandboxClient.__new__(DockerSandboxClient)
    manager._client = client

    manager.stop_and_remove("container-id")
    container.stop.assert_called_once_with(timeout=5)
    container.remove.assert_called_once_with(force=True)
