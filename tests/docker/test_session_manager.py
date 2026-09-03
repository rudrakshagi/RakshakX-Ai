"""Unit tests for sandbox session manager orchestration (mocked docker)."""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rakshak.runtime import session_manager
from rakshak.runtime.session_manager import _find_free_port, cleanup, create_or_reuse


def test_find_free_port_returns_int():
    port = _find_free_port()
    assert isinstance(port, int)
    assert 0 < port < 65536


def test_find_free_port_is_bindable():
    port = _find_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", port))


@pytest.mark.asyncio
async def test_create_or_reuse_caches(tmp_path):
    bundle = MagicMock()
    session_manager._SESSION_CACHE["scan1"] = bundle
    try:
        got = await create_or_reuse("scan1")
        assert got is bundle
    finally:
        session_manager._SESSION_CACHE.clear()


@pytest.mark.asyncio
async def test_cleanup_removes_container(monkeypatch):
    bundle = MagicMock()
    bundle.session.docker_client.stop_and_remove = MagicMock()
    session_manager._SESSION_CACHE["scan1"] = bundle
    await cleanup("scan1")
    bundle.session.docker_client.stop_and_remove.assert_called_once()
    assert "scan1" not in session_manager._SESSION_CACHE


@pytest.mark.asyncio
async def test_create_missing_local_source_skipped(monkeypatch, tmp_path):
    """local_sources whose host path doesn't exist should be ignored."""
    from rakshak.runtime.docker_client import DockerSandboxClient

    settings = MagicMock()
    settings.runtime.docker_image = "rakshakx/sandbox:latest"
    settings.runtime.enable_caido = False

    monkeypatch.setattr(session_manager, "load_settings", lambda: settings)

    docker_client = MagicMock(spec=DockerSandboxClient)
    docker_client.ensure_image = MagicMock()
    container = MagicMock()
    docker_client.create_sandbox.return_value = container

    with (
        patch.object(session_manager, "DockerSandboxClient", return_value=docker_client),
        patch.object(session_manager, "bootstrap_caido", AsyncMock(return_value=None)),
    ):
        await create_or_reuse(
            "scan2",
            local_sources=[{"source_path": "/definitely/missing/path", "workspace_subdir": "target"}],
        )

    args, kwargs = docker_client.create_sandbox.call_args
    assert kwargs.get("bind_mounts") == []
    session_manager._SESSION_CACHE.clear()
