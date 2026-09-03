"""Unit tests for SDKSandboxSession adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rakshak.runtime.sdk_session import SDKSandboxSession


def _make_session():
    container = MagicMock()
    docker_client = MagicMock()
    return SDKSandboxSession(container=container, docker_client=docker_client)


@pytest.mark.asyncio
async def test_exec_internal_truncates_4k():
    s = _make_session()
    s._docker_client.exec_command.return_value = (0, "x" * 10_000)
    result = await s._exec_internal("echo", "hi")
    decoded = result.stdout.decode("utf-8")
    assert "Output truncated" in decoded or len(decoded) <= 4100


@pytest.mark.asyncio
async def test_exec_internal_short_passthrough():
    s = _make_session()
    s._docker_client.exec_command.return_value = (0, "short output")
    result = await s._exec_internal("echo", "hi")
    assert result.stdout.decode("utf-8") == "short output"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_running_true():
    s = _make_session()
    s._container.reload = MagicMock()
    s._container.status = "running"
    assert await s.running() is True


@pytest.mark.asyncio
async def test_running_false():
    s = _make_session()
    s._container.reload = MagicMock()
    s._container.status = "exited"
    assert await s.running() is False


@pytest.mark.asyncio
async def test_running_exception_returns_false():
    s = _make_session()
    s._container.reload = MagicMock(side_effect=Exception("gone"))
    assert await s.running() is False


@pytest.mark.asyncio
async def test_read_bridges_to_client():
    s = _make_session()
    s._docker_client.read_file.return_value = "file contents"
    out = await s.read(Path("/workspace/x.txt"))
    assert out.read().decode("utf-8") == "file contents"


@pytest.mark.asyncio
async def test_read_missing_raises():
    s = _make_session()
    s._docker_client.read_file.side_effect = FileNotFoundError("missing")
    with pytest.raises(FileNotFoundError):
        await s.read(Path("/nope.txt"))


@pytest.mark.asyncio
async def test_write_bridges_to_client():
    import io

    s = _make_session()
    await s.write(Path("/workspace/out.txt"), io.BytesIO(b"payload"))
    s._docker_client.write_file.assert_called_once()
