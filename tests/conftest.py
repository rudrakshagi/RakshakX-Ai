"""Shared pytest fixtures for RakshakX tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from rakshak.core import paths
from rakshak.core.agents import AgentCoordinator
from rakshak.report.state import set_global_report_state
from rakshak.runtime import session_manager
from rakshak.tools.notes.tools import _NOTES
from rakshak.tools.output_store import configure_spill_writer
from rakshak.tools.todo.tools import _TODOS


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live-target E2E that spends real LLM tokens",
    )


@pytest.fixture
def run_live(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--run-live"))


@pytest.fixture(autouse=True)
def _isolate_globals(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Reset module-level mutable singletons between tests and point runs_dir at tmp."""
    _NOTES.clear()
    _TODOS.clear()
    session_manager._SESSION_CACHE.clear()
    configure_spill_writer(None)
    set_global_report_state(None)

    def _tmp_base() -> Path:
        return Path("/tmp/rakshak-test-runs")

    monkeypatch.setattr(paths, "base_runs_dir", _tmp_base)
    yield
    _NOTES.clear()
    _TODOS.clear()
    session_manager._SESSION_CACHE.clear()
    configure_spill_writer(None)
    set_global_report_state(None)


@pytest.fixture
async def coordinator() -> AgentCoordinator:
    return AgentCoordinator()


class FakeUsage:
    """Minimal stand-in for SDK token usage objects."""

    def __init__(self, total_tokens: int = 100, prompt_tokens: int = 70, completion_tokens: int = 30) -> None:
        self.total_tokens = total_tokens
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class FakeRunResult:
    """Minimal stand-in for an SDK RunResult."""

    def __init__(self, final_output: str | None = None, usage: Any = None) -> None:
        self.final_output = final_output
        self.usage = usage or FakeUsage()


@pytest.fixture
def fake_usage() -> FakeUsage:
    return FakeUsage()


@pytest.fixture
def fake_result() -> FakeRunResult:
    return FakeRunResult()


def docker_available() -> bool:
    """Return True if the Docker daemon is reachable, else False."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:
        return False


async def invoke_tool(tool, context, **kwargs):
    """Invoke a wrapped FunctionTool by passing args as JSON via on_invoke_tool.

    Returns the tool's string output (encoding a JSON result for these tools).
    """
    import json as _json

    from agents.tool import ToolContext

    serialized = _json.dumps(kwargs)
    ctx = ToolContext(
        context=context,
        tool_name=tool.name,
        tool_arguments=serialized,
        tool_call_id="call_test",
    )
    return await tool.on_invoke_tool(ctx, serialized)


@pytest.fixture(scope="session")
def requires_docker() -> bool:
    """Skip the test if Docker is not available."""
    return docker_available()
