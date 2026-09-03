"""Unit tests for notes and todos tools."""

from __future__ import annotations

import asyncio
import json

from rakshak.tools.notes.tools import create_note, list_notes
from rakshak.tools.todo.tools import create_todo, list_todos, mark_todo_done
from tests.conftest import invoke_tool


def test_create_note_and_list():
    asyncio.run(invoke_tool(create_note, {}, title="endpoint", content="http://x/api"))
    asyncio.run(invoke_tool(create_note, {}, title="cred", content="user:pass"))
    res = asyncio.run(invoke_tool(list_notes, {}))
    payload = json.loads(res)
    assert payload["success"] is True
    assert set(payload["notes"]) == {"endpoint", "cred"}


def test_create_todo_list_done():
    asyncio.run(invoke_tool(create_todo, {}, id="t1", task="Probe /api"))
    asyncio.run(invoke_tool(create_todo, {}, id="t2", task="Check JWT"))
    asyncio.run(invoke_tool(mark_todo_done, {}, id="t1"))

    res = asyncio.run(invoke_tool(list_todos, {}))
    payload = json.loads(res)
    by_id = {t["id"]: t["status"] for t in payload["todos"]}
    assert by_id["t1"] == "done"
    assert by_id["t2"] == "pending"


def test_mark_todo_missing():
    res = asyncio.run(invoke_tool(mark_todo_done, {}, id="nope"))
    payload = json.loads(res)
    assert payload["success"] is False
