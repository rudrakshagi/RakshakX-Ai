"""Agent session storage and SQLite persistence helpers."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator, cast
from weakref import WeakKeyDictionary

from agents.items import ItemHelpers
from agents.memory import SQLiteSession

if TYPE_CHECKING:
    from agents.items import TResponseInputItem
    from agents.memory import Session

logger = logging.getLogger(__name__)

# Track write locks per session so compaction or out-of-band mailbox injection
# doesn't race against the active agent runner turn
_session_write_locks: WeakKeyDictionary[Session, asyncio.Lock] = WeakKeyDictionary()


class _PooledConnectionSession(SQLiteSession):
    """SQLiteSession that avoids SQLite cross-thread locks across async agent loops."""

    @contextmanager
    def _locked_connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            if self._closed:
                raise RuntimeError("SQLiteSession is closed")
            if self._is_memory_db:
                yield self._shared_connection
                return
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                yield conn
            finally:
                conn.close()


def open_agent_session(agent_id: str, path: Path) -> SQLiteSession:
    """Open or create a persistent SQLite session for the given agent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return _PooledConnectionSession(session_id=agent_id, db_path=path)


def session_write_lock(session: Session) -> asyncio.Lock:
    """Retrieve or create the serialization lock for this session instance."""
    lock = _session_write_locks.get(session)
    if lock is None:
        lock = asyncio.Lock()
        _session_write_locks[session] = lock
    return lock


async def seed_initial_input(session: Session, initial_input: Any) -> bool:
    """Seed the opening system/task identity into an agent's session if empty."""
    items = ItemHelpers.input_to_new_input_list(initial_input)
    if not items:
        return False
    async with session_write_lock(session):
        if await session.get_items():
            return False
        await session.add_items(items)
    return True


_IMAGE_ELIDED_TEXT = "[older screenshot elided to preserve context memory]"
_INHERITED_IMAGE_TEXT = "[screenshot omitted from inherited parent context]"


def _output_has_image(item_dict: dict[str, Any]) -> bool:
    return (
        item_dict.get("type") == "function_call_output"
        and isinstance(item_dict.get("output"), list)
        and any(
            isinstance(b, dict) and b.get("type") == "input_image"
            for b in item_dict["output"]
        )
    )


def _elided_output(item_dict: dict[str, Any], text: str) -> dict[str, Any]:
    output = item_dict.get("output")
    blocks = output if isinstance(output, list) else []
    return {
        "type": "function_call_output",
        "call_id": item_dict.get("call_id"),
        "output": [
            {"type": "input_text", "text": text}
            if isinstance(block, dict) and block.get("type") == "input_image"
            else block
            for block in blocks
        ],
    }


async def _rewrite_session(
    session: Session,
    transform: Callable[[list[Any]], tuple[list[Any], bool]],
) -> bool:
    """Atomically read, transform, and write session items; rollback on failure."""
    async with session_write_lock(session):
        items = await session.get_items()
        if not items:
            return False
        rebuilt, changed = transform(list(items))
        if not changed:
            return False
        rebuilt_items = cast("list[TResponseInputItem]", rebuilt)
        original_items = cast("list[TResponseInputItem]", list(items))
        await session.clear_session()
        try:
            await session.add_items(rebuilt_items)
        except Exception:
            logger.exception("Session rewrite failed; rolling back to original state")
            await session.clear_session()
            await session.add_items(original_items)
            raise
        return True


async def replace_session_items(
    session: Session,
    new_items: list[Any],
    *,
    expected_len: int | None = None,
) -> bool:
    """Safely overwrite the entire session history with new compacted turns."""
    async with session_write_lock(session):
        original = list(await session.get_items())
        if expected_len is not None and len(original) != expected_len:
            logger.warning(
                "Skipping session rewrite: expected %d items, found %d (concurrent modification)",
                expected_len,
                len(original),
            )
            return False
        rebuilt = cast("list[TResponseInputItem]", new_items)
        await session.clear_session()
        try:
            await session.add_items(rebuilt)
            return True
        except Exception:
            logger.exception("Failed to replace session items; restoring original history")
            await session.clear_session()
            await session.add_items(cast("list[TResponseInputItem]", original))
            raise


async def enforce_image_budget(session: Session, max_images: int = 5) -> bool:
    """Retain only the latest N screenshots, eliding older image blocks to save tokens."""
    def _transform(items: list[Any]) -> tuple[list[Any], bool]:
        # Identify indices with image outputs
        image_indices = [
            i for i, item in enumerate(items)
            if isinstance(item, dict) and _output_has_image(item)
        ]
        if len(image_indices) <= max_images:
            return items, False

        to_elide = set(image_indices[:-max_images])
        out: list[Any] = []
        for i, item in enumerate(items):
            if i in to_elide and isinstance(item, dict):
                out.append(_elided_output(item, _IMAGE_ELIDED_TEXT))
            else:
                out.append(item)
        return out, True

    return await _rewrite_session(session, _transform)


async def strip_all_images_from_session(session: Session) -> bool:
    """Remove all heavy image binaries before handing history to a subagent."""
    def _transform(items: list[Any]) -> tuple[list[Any], bool]:
        changed = False
        out: list[Any] = []
        for item in items:
            if isinstance(item, dict) and _output_has_image(item):
                out.append(_elided_output(item, _INHERITED_IMAGE_TEXT))
                changed = True
            else:
                out.append(item)
        return out, changed

    return await _rewrite_session(session, _transform)
