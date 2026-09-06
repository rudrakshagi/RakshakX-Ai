"""Unit tests for Phase-2 runtime-harness changes (all docker mocked).

Covers:
- ``rakshak.interface.viewer.server._is_scan_container_name`` predicate.
- ``DockerSandboxClient.remove_container_by_name`` (NotFound -> False).
- ``create_or_reuse`` port-collision retry (3 attempts, fresh ports).
- ``create_or_reuse`` stale same-name removal before create.
- ``bootstrap_caido`` post-readiness retry (login fail-once -> success;
  always-fail -> RuntimeError).
- ``SandboxSession.exec/write/read`` running off the event loop via
  ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from docker.errors import APIError, NotFound

from rakshak.interface.viewer.server import _is_scan_container_name
from rakshak.runtime import caido_bootstrap, session_manager
from rakshak.runtime.docker_client import DockerSandboxClient
from rakshak.runtime.session_manager import SandboxSession, create_or_reuse


# 1. Scan-container name predicate -------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("rakshak-abc123", True),
        ("rakshak-scan-deadbeef", True),
        ("rakshak-", True),  # bare prefix still matches scan namespace
        ("rakshakx-juice-shop", False),  # target app — never reap
        ("rakshakx-dvwa", False),  # target app — never reap
        ("other", False),
        ("", False),
    ],
)
def test_is_scan_container_name(name: str, expected: bool) -> None:
    assert _is_scan_container_name(name) is expected


# 2. remove_container_by_name -------------------------------------------------


def _client_without_init() -> DockerSandboxClient:
    mgr = DockerSandboxClient.__new__(DockerSandboxClient)
    mgr._client = MagicMock()
    return mgr


def test_remove_container_by_name_not_found_returns_false() -> None:
    mgr = _client_without_init()
    mgr._client.containers.get.side_effect = NotFound("missing")
    assert mgr.remove_container_by_name("rakshak-gone") is False
    mgr._client.containers.get.assert_called_once_with("rakshak-gone")


def test_remove_container_by_name_stops_and_removes() -> None:
    mgr = _client_without_init()
    container = MagicMock()
    mgr._client.containers.get.return_value = container
    assert mgr.remove_container_by_name("rakshak-old") is True
    mgr._client.containers.get.assert_called_once_with("rakshak-old")
    container.stop.assert_called_once_with(timeout=5)
    container.remove.assert_called_once_with(force=True)


# 3. Port-collision retry ------------------------------------------------------

_PORT_ERR = "port is already allocated"


def _fake_settings(*, enable_caido: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        runtime=SimpleNamespace(
            docker_image="rakshakx/sandbox:latest",
            enable_caido=enable_caido,
        )
    )


def _stub_runtime_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    create_side_effect,
    enable_caido: bool = True,
) -> list:
    """Stub constructor-level deps; return the create_sandbox call log."""
    calls: list = []

    def _recording_create(self, **kwargs):
        calls.append(kwargs)
        eff = create_side_effect() if callable(create_side_effect) else create_side_effect
        if isinstance(eff, Exception):
            raise eff
        return eff

    monkeypatch.setattr(session_manager, "load_settings", lambda: _fake_settings(enable_caido=enable_caido))
    monkeypatch.setattr(DockerSandboxClient, "__init__", lambda self: setattr(self, "_client", MagicMock()))
    monkeypatch.setattr(DockerSandboxClient, "ensure_image", lambda self, image: None)
    monkeypatch.setattr(DockerSandboxClient, "remove_container_by_name", lambda self, name: False)
    monkeypatch.setattr(DockerSandboxClient, "create_sandbox", _recording_create)
    monkeypatch.setattr(session_manager, "_find_free_port", lambda: 51234)
    monkeypatch.setattr(session_manager, "bootstrap_caido", AsyncMock(return_value=None))
    return calls


async def test_port_collision_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    container = MagicMock()
    attempts = {"n": 0}

    def _flaky():
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise APIError(_PORT_ERR)
        return container

    calls = _stub_runtime_harness(monkeypatch, create_side_effect=_flaky)
    bundle = await create_or_reuse("port-retry-scan")
    assert bundle.container is container
    assert attempts["n"] == 3
    assert len(calls) == 3


async def test_port_collision_always_raises_after_three(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"n": 0}

    def _always():
        attempts["n"] += 1
        raise APIError(_PORT_ERR)

    _stub_runtime_harness(monkeypatch, create_side_effect=_always)
    with pytest.raises(APIError):
        await create_or_reuse("port-always-scan")
    assert attempts["n"] == 3


async def test_non_port_apierror_raises_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"n": 0}

    def _boom():
        attempts["n"] += 1
        raise APIError("boom")

    _stub_runtime_harness(monkeypatch, create_side_effect=_boom)
    with pytest.raises(APIError):
        await create_or_reuse("port-boom-scan")
    assert attempts["n"] == 1


# 4. Stale same-name removal happens BEFORE create ------------------------------


async def test_stale_same_name_removed_before_create(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    container = MagicMock()

    def _fake_remove(self, name: str) -> bool:
        order.append(f"remove:{name}")
        return True

    def _fake_create(self, **kwargs):
        order.append(f"create:{kwargs.get('name')}")
        return container

    monkeypatch.setattr(session_manager, "load_settings", lambda: _fake_settings(enable_caido=False))
    monkeypatch.setattr(DockerSandboxClient, "__init__", lambda self: setattr(self, "_client", MagicMock()))
    monkeypatch.setattr(DockerSandboxClient, "ensure_image", lambda self, image: None)
    monkeypatch.setattr(DockerSandboxClient, "remove_container_by_name", _fake_remove)
    monkeypatch.setattr(DockerSandboxClient, "create_sandbox", _fake_create)
    monkeypatch.setattr(session_manager, "bootstrap_caido", AsyncMock(return_value=None))

    bundle = await create_or_reuse("stale123")
    assert bundle.container is container
    assert order == ["remove:rakshak-stale123", "create:rakshak-stale123"]


# 5. Caido post-readiness retry -------------------------------------------------


def _ready_post_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"content-type": "application/json"}
    resp.json.return_value = {"data": {"__typename": "Query"}}
    return resp


def _stub_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    monkeypatch.setattr(
        httpx.AsyncClient,
        "post",
        AsyncMock(return_value=_ready_post_response()),
    )


async def test_caido_login_retry_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_readiness(monkeypatch)
    sentinel = object()
    login = AsyncMock(side_effect=[RuntimeError("transient 502"), "tok-1"])
    monkeypatch.setattr(caido_bootstrap, "guest_login", login)
    monkeypatch.setattr(caido_bootstrap, "ensure_project", AsyncMock(return_value="proj-1"))
    monkeypatch.setattr(caido_bootstrap, "_connect_sdk", AsyncMock(return_value=sentinel))

    out = await caido_bootstrap.bootstrap_caido(
        59999, retries=1, delay=0.01, post_ready_retries=3
    )
    assert out is sentinel
    assert login.await_count == 2


async def test_caido_login_always_fails_raises_runtimeerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_readiness(monkeypatch)
    login = AsyncMock(side_effect=RuntimeError("down"))
    monkeypatch.setattr(caido_bootstrap, "guest_login", login)
    monkeypatch.setattr(caido_bootstrap, "ensure_project", AsyncMock(return_value="proj-1"))
    monkeypatch.setattr(caido_bootstrap, "_connect_sdk", AsyncMock(return_value=object()))

    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        await caido_bootstrap.bootstrap_caido(
            59999, retries=1, delay=0.01, post_ready_retries=3
        )
    assert login.await_count == 3


async def test_caido_import_error_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_readiness(monkeypatch)
    login = AsyncMock(side_effect=ImportError("no caido-sdk-client"))
    monkeypatch.setattr(caido_bootstrap, "guest_login", login)
    out = await caido_bootstrap.bootstrap_caido(
        59999, retries=1, delay=0.01, post_ready_retries=3
    )
    assert out is None
    assert login.await_count == 1  # no retry on missing package


# 6. SandboxSession.exec/write/read off the event loop --------------------------


def _blocking_session(block_s: float = 1.5) -> SandboxSession:
    container = MagicMock()
    docker_client = MagicMock()

    def _exec(*args, **kwargs):
        time.sleep(block_s)
        return (0, "done")

    docker_client.exec_command.side_effect = _exec
    return SandboxSession(container=container, docker_client=docker_client)


async def test_exec_runs_off_event_loop() -> None:
    session = _blocking_session(block_s=1.5)
    tick_at: dict[str, float] = {}
    start = time.monotonic()

    async def marker() -> None:
        await asyncio.sleep(0.2)
        tick_at["t"] = time.monotonic()

    (exec_res, _) = await asyncio.gather(session.exec("echo hi"), marker())
    code, out = exec_res
    assert code == 0
    assert out == "done"
    assert "t" in tick_at
    assert tick_at["t"] - start < 1.5


async def test_write_delegates_off_event_loop() -> None:
    container = MagicMock()
    docker_client = MagicMock()
    session = SandboxSession(container=container, docker_client=docker_client)
    await session.write("/workspace/x.txt", "hello")
    docker_client.write_file.assert_called_once_with(container, "/workspace/x.txt", "hello")


async def test_read_delegates_off_event_loop() -> None:
    container = MagicMock()
    docker_client = MagicMock()
    docker_client.read_file.return_value = "file-content"
    session = SandboxSession(container=container, docker_client=docker_client)
    out = await session.read("/workspace/x.txt")
    assert out == "file-content"
    docker_client.read_file.assert_called_once_with(container, "/workspace/x.txt")


async def test_write_read_roundtrip_blocking_stays_responsive() -> None:
    container = MagicMock()
    docker_client = MagicMock()
    docker_client.write_file.side_effect = lambda *a, **k: time.sleep(1.0)
    docker_client.read_file.side_effect = lambda *a, **k: (time.sleep(1.0), "v")[1]
    session = SandboxSession(container=container, docker_client=docker_client)

    ticked: list[bool] = []

    async def marker() -> None:
        await asyncio.sleep(0.2)
        ticked.append(True)

    await asyncio.gather(session.write("/workspace/a.txt", "x"), marker())
    assert ticked == [True]
    ticked.clear()
    out = await asyncio.gather(session.read("/workspace/a.txt"), marker())
    assert out[0] == "v"
    assert ticked == [True]
