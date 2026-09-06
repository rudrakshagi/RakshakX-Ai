"""Unit tests for the Phase-3 tool harness (mocked, no real docker).

Covers:
- ``rakshak.tools.errors`` model failure/timeout hooks (JSON envelope + hints).
- ``@function_tool`` hook wiring across all tool modules.
- ``output_store`` spill-writer resolution (ambient ContextVar vs global).
- ``bound_text`` head+tail bounding.
- ``bound_and_store`` spill behavior.
- ``SDKSandboxSession._exec_internal`` bounding via ``bound_and_store``.
"""

from __future__ import annotations

import importlib
import json
from unittest.mock import MagicMock

import pytest

from agents.tool import FunctionTool

from rakshak.runtime.sdk_session import SDKSandboxSession
from rakshak.tools import output_store as output_store_mod
from rakshak.tools.errors import model_failure_message, model_timeout_message
from rakshak.tools.output_store import (
    bound_and_store,
    bound_text,
    configure_spill_writer,
)


@pytest.fixture(autouse=True)
def _clean_spill_writer():
    configure_spill_writer(None)
    yield
    configure_spill_writer(None)


# 1. errors.py ---------------------------------------------------------------

FAILURE_CASES = [
    ValueError("bad argument value"),
    ConnectionError("connection refused by target 10.0.0.1:8080"),
    FileNotFoundError("No such file or directory: '/nope/x.txt'"),
    TimeoutError("operation timed out after 30s"),
    RuntimeError("something completely unexpected broke"),
]


@pytest.mark.parametrize("error", FAILURE_CASES, ids=[type(e).__name__ for e in FAILURE_CASES])
def test_failure_message_envelope(error: Exception) -> None:
    raw = model_failure_message(None, error)
    parsed = json.loads(raw)  # must be valid JSON
    assert parsed["success"] is False
    assert parsed["error"], "error cause must be non-empty"
    assert parsed["hint"], "hint must be non-empty"
    assert "\n" not in parsed["error"], "multiline cause must collapse to one line"


def test_failure_message_connection_hint_guides_retry() -> None:
    parsed = json.loads(model_failure_message(None, ConnectionError("connection refused")))
    hint = parsed["hint"].lower()
    assert "up" in hint or "retry" in hint


def test_failure_message_timeout_hint_narrows() -> None:
    parsed = json.loads(model_failure_message(None, TimeoutError("query timed out")))
    assert "NARROWER" in parsed["hint"]


def test_timeout_message_narrower_guidance() -> None:
    for error in (TimeoutError("timed out"), TimeoutError("deadline exceeded")):
        parsed = json.loads(model_timeout_message(None, error))
        assert parsed["success"] is False
        assert parsed["error"], "timeout cause must be non-empty"
        assert "NARROWER" in parsed["hint"]


def test_failure_message_multiline_collapsed() -> None:
    error = ValueError("first line\nsecond line\n   third  line")
    parsed = json.loads(model_failure_message(None, error))
    assert "\n" not in parsed["error"]
    assert "first line" in parsed["error"] and "third line" in parsed["error"]


# 2. Hook wiring --------------------------------------------------------------

_TOOL_MODULE_NAMES = [
    "rakshak.tools.agents_graph.tools",
    "rakshak.tools.todo.tools",
    "rakshak.tools.reporting.tool",
    "rakshak.tools.notes.tools",
    "rakshak.tools.proxy.tools",
    "rakshak.tools.load_skill.tool",
    "rakshak.tools.finish.tool",
    "rakshak.tools.thinking.tool",
]


def _discover_tools() -> list[FunctionTool]:
    found: list[FunctionTool] = []
    for name in _TOOL_MODULE_NAMES:
        module = importlib.import_module(name)
        found.extend(
            obj for obj in vars(module).values() if isinstance(obj, FunctionTool)
        )
    return found


def _failure_hook(tool: FunctionTool):
    # The agents SDK stores the failure hook as `_failure_error_function`
    # (public alias may not exist); accept either spelling.
    hook = getattr(tool, "failure_error_function", None)
    if hook is None:
        hook = getattr(tool, "_failure_error_function", None)
    return hook


def test_all_tools_wire_failure_and_timeout_hooks() -> None:
    tools = _discover_tools()
    assert len(tools) >= 17, f"expected >= 17 FunctionTools, found {len(tools)}"
    for tool in tools:
        assert _failure_hook(tool) is not None, f"{tool.name} missing failure hook"
        assert tool.timeout_error_function is not None, (
            f"{tool.name} missing timeout hook"
        )
        assert callable(_failure_hook(tool))
        assert callable(tool.timeout_error_function)


def test_wired_failure_hook_returns_actionable_json() -> None:
    tools = _discover_tools()
    assert tools, "expected at least one FunctionTool"
    parsed = json.loads(_failure_hook(tools[0])(None, ValueError("boom")))
    assert parsed == {"success": False, "error": parsed["error"], "hint": parsed["hint"]}
    assert parsed["success"] is False and parsed["hint"]


# 3. Spill writer resolution ---------------------------------------------------

async def _ambient_writer(output_id: str, text: str) -> str:
    return f"/ambient/{output_id}.txt"


async def _global_writer(output_id: str, text: str) -> str:
    return f"/global/{output_id}.txt"


def test_ambient_spill_writer_beats_global() -> None:
    try:
        configure_spill_writer(_ambient_writer)  # sets ambient + global to ambient
        output_store_mod._spill_writer = _global_writer  # diverge the fallback
        assert output_store_mod._resolve_spill_writer() is _ambient_writer
    finally:
        configure_spill_writer(None)


def test_global_fallback_when_ambient_none() -> None:
    try:
        configure_spill_writer(None)
        output_store_mod._spill_writer = _global_writer  # fallback only
        output_store_mod._active_spill_writer.set(None)  # no ambient writer
        assert output_store_mod._resolve_spill_writer() is _global_writer
    finally:
        configure_spill_writer(None)


def test_configure_none_clears_both_writers() -> None:
    try:
        configure_spill_writer(_ambient_writer)
        assert output_store_mod._resolve_spill_writer() is not None
    finally:
        configure_spill_writer(None)
    assert output_store_mod._spill_writer is None
    assert output_store_mod._resolve_spill_writer() is None


# 4. bound_text head+tail ------------------------------------------------------

def test_bound_text_head_and_tail_lines() -> None:
    text = "\n".join(f"line {i}" for i in range(1000))
    out = bound_text(text, max_lines=10)
    assert "Output truncated" in out
    assert "head+tail" in out
    assert "omitted in the middle" in out
    assert "line 0" in out  # head survives
    assert "line 999" in out  # tail survives
    assert out.count("line ") <= 12, "only head+tail lines should be kept"


def test_bound_text_byte_cap_single_huge_line() -> None:
    text = "HEADMARK" + "x" * 200_000 + "TAILMARK"
    out = bound_text(text, max_lines=500, max_bytes=1000)
    assert "Output truncated" in out
    assert "HEADMARK" in out
    assert "TAILMARK" in out
    assert len(out) < 2000


def test_bound_text_short_passthrough() -> None:
    assert bound_text("hello world") == "hello world"


def test_bound_text_empty_passthrough() -> None:
    assert bound_text("") == ""


# 5. bound_and_store spill -----------------------------------------------------

async def test_bound_and_store_spills_full_text_with_header() -> None:
    received: list[tuple[str, str]] = []

    async def writer(output_id: str, text: str) -> str:
        received.append((output_id, text))
        return f"/workspace/.rakshak/spill/{output_id}.txt"

    try:
        configure_spill_writer(writer)
        big = "\n".join(f"row {i}" for i in range(5000))
        out = await bound_and_store(big)
        assert "[NOTE: Full output" in out
        assert "/workspace/.rakshak/spill/" in out
        assert "Output truncated" in out
        assert len(received) == 1
        assert received[0][1] == big, "writer must receive FULL untruncated text"
    finally:
        configure_spill_writer(None)


async def test_bound_and_store_without_writer_has_no_note_header() -> None:
    configure_spill_writer(None)
    big = "\n".join(f"row {i}" for i in range(5000))
    out = await bound_and_store(big)
    assert "[NOTE" not in out
    assert "Output truncated" in out


# 6. sdk_session uses bound_and_store ------------------------------------------

def _make_session() -> SDKSandboxSession:
    container = MagicMock()
    docker_client = MagicMock()
    return SDKSandboxSession(container=container, docker_client=docker_client)


async def test_exec_internal_bounds_oversized_output() -> None:
    session = _make_session()
    session._docker_client.exec_command.return_value = (0, "x" * 10_000)
    result = await session._exec_internal("echo", "hi")
    decoded = result.stdout.decode("utf-8")
    assert "Output truncated" in decoded
    assert "[output truncated by RakshakX: exceeded 4k chars]" not in decoded


async def test_exec_internal_small_output_byte_identical() -> None:
    session = _make_session()
    session._docker_client.exec_command.return_value = (0, "short output")
    result = await session._exec_internal("echo", "hi")
    assert result.stdout == b"short output"
    assert result.exit_code == 0
