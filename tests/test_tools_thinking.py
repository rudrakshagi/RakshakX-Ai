"""Unit tests for think tool."""

from __future__ import annotations

import asyncio
import json

from rakshak.tools.thinking.tool import think
from tests.conftest import invoke_tool


def test_think_returns_success():
    res = asyncio.run(invoke_tool(think, {}, thought="plan next"))
    payload = json.loads(res)
    assert payload["success"] is True
    assert payload["status"] == "thought_recorded"
