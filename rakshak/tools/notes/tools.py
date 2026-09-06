"""Scratchpad notes tools for persistent attack surface reconnaissance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from agents import RunContextWrapper, function_tool

from rakshak.tools.errors import model_failure_message, model_timeout_message

_NOTES: dict[str, str] = {}


def hydrate_notes_from_disk(state_dir: Path) -> None:
    """Load notes from disk on scan resume."""
    notes_file = state_dir / "notes.json"
    if notes_file.exists():
        try:
            data = json.loads(notes_file.read_text(encoding="utf-8"))
            _NOTES.update(data)
        except Exception:
            pass


@function_tool(
    timeout=10,
    failure_error_function=model_failure_message,
    timeout_error_function=model_timeout_message,
)
async def create_note(
    ctx: RunContextWrapper,
    title: Annotated[str, "Short unique title for the note."],
    content: Annotated[str, "Full note body (e.g. leaked endpoints, creds, token structures)."],
) -> str:
    """Create a persistent research note (e.g. leaked endpoints, creds, token structures)."""
    _NOTES[title] = content
    return json.dumps({"success": True, "title": title, "length": len(content)})


@function_tool(
    timeout=10,
    failure_error_function=model_failure_message,
    timeout_error_function=model_timeout_message,
)
async def list_notes(ctx: RunContextWrapper) -> str:
    """List titles of all recorded research notes."""
    return json.dumps({"success": True, "notes": list(_NOTES.keys())})


@function_tool(
    timeout=10,
    failure_error_function=model_failure_message,
    timeout_error_function=model_timeout_message,
)
async def get_note(
    ctx: RunContextWrapper,
    title: Annotated[str, "Title of the note to retrieve."],
) -> str:
    """Retrieve full content of a previously saved note."""
    if title in _NOTES:
        return json.dumps({"success": True, "title": title, "content": _NOTES[title]})
    return json.dumps({"success": False, "error": f"Note '{title}' not found."})
