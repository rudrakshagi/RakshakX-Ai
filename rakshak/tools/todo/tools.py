"""Persistent task checklist tools for pentesting workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

from agents import RunContextWrapper, function_tool


@dataclass
class TodoItem:
    id: str
    task: str
    status: str = "pending"  # "pending" | "done"


_TODOS: dict[str, TodoItem] = {}


def hydrate_todos_from_disk(state_dir: Path) -> None:
    """Load persistent todo items from state directory."""
    todo_file = state_dir / "todos.json"
    if todo_file.exists():
        try:
            data = json.loads(todo_file.read_text(encoding="utf-8"))
            for item in data:
                _TODOS[item["id"]] = TodoItem(**item)
        except Exception:
            pass


def _persist_todos(state_dir: Path | None) -> None:
    if state_dir is not None:
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            payload = [asdict(t) for t in _TODOS.values()]
            (state_dir / "todos.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass


@function_tool(timeout=10)
async def create_todo(
    ctx: RunContextWrapper,
    id: Annotated[str, "Unique identifier for the task (short slug)."],
    task: Annotated[str, "Human-readable description of the task."],
) -> str:
    """Create a new task item in your pentest work checklist."""
    _TODOS[id] = TodoItem(id=id, task=task, status="pending")
    return json.dumps({"success": True, "created": id, "task": task})


@function_tool(timeout=10)
async def list_todos(ctx: RunContextWrapper) -> str:
    """List all current pending and completed tasks."""
    items = [asdict(t) for t in _TODOS.values()]
    return json.dumps({"success": True, "todos": items}, indent=2)


@function_tool(timeout=10)
async def mark_todo_done(
    ctx: RunContextWrapper,
    id: Annotated[str, "Identifier of the task to mark as completed."],
) -> str:
    """Mark an assigned task as completed."""
    if id in _TODOS:
        _TODOS[id].status = "done"
        return json.dumps({"success": True, "id": id, "status": "done"})
    return json.dumps({"success": False, "error": f"Todo '{id}' not found."})
