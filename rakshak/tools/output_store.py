"""Tool output bounding and sandbox spillage store."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Directory inside the sandbox container workspace where spilled tool outputs land
WORKSPACE_SPILL_DIR = "/workspace/.rakshak/spill"

# Callback registered by the scan runner to stream oversized output to the sandbox filesystem
SpillWriter = Callable[[str, str], Awaitable[str | None]]
_spill_writer: SpillWriter | None = None

# Ambient per-scan writer. The module-global above is a fallback for tools
# invoked outside a scan context; concurrent scans in one process must NOT
# share a writer (last-writer-wins would spill scan A's output into scan B's
# sandbox), so the runner binds the ambient writer per scan and tools prefer it.
_active_spill_writer: ContextVar[SpillWriter | None] = ContextVar(
    "rakshak_spill_writer", default=None
)


def configure_spill_writer(writer: SpillWriter | None) -> None:
    """Register or clear the active sandbox file spill writer (ambient + fallback)."""
    global _spill_writer  # noqa: PLW0603
    _spill_writer = writer
    _active_spill_writer.set(writer)


def _resolve_spill_writer() -> SpillWriter | None:
    return _active_spill_writer.get() or _spill_writer


def _estimate_chars(text: str) -> int:
    """Rough char-based token estimate (1 token ~= 3 chars for mixed code/text)."""
    return len(text) // 3


def _head_tail_split(text: str, budget: int) -> tuple[str, str]:
    """Split text into (head, tail) halves of ~budget/2 chars each."""
    if len(text) <= budget:
        return text, ""
    half = budget // 2
    return text[:half], text[-half:]


def bound_text(
    text: str,
    *,
    max_lines: int = 500,
    max_bytes: int = 100_000,
    max_tokens: int = 12_000,
) -> str:
    """Bound oversized text with a head+tail window and a clean omission marker.

    Unlike head-only truncation, the TAIL (exit codes, error summaries,
    "found N items" footers) survives — that is where scan tools report
    their verdict. The middle is cut with exact omitted counts.
    """
    if not text:
        return text

    encoded = text.encode("utf-8")
    lines = text.splitlines(keepends=True)
    total_lines = len(lines)
    total_bytes = len(encoded)
    capped = (
        total_bytes > max_bytes
        or total_lines > max_lines
        or _estimate_chars(text) > max_tokens
    )
    if not capped:
        return text

    # Line window: first half + last half of max_lines.
    head_n = max_lines // 2
    tail_n = max_lines - head_n
    if total_lines > max_lines:
        head, tail = lines[:head_n], lines[-tail_n:]
    else:
        head, tail = lines, []

    kept = "".join(head) + "".join(tail)

    # Byte window on the kept text (decode-safe slices).
    kept_bytes = kept.encode("utf-8")
    if len(kept_bytes) > max_bytes:
        half = max_bytes // 2
        head_b = kept_bytes[:half].decode("utf-8", errors="ignore")
        tail_b = kept_bytes[-half:].decode("utf-8", errors="ignore")
        kept = head_b + tail_b

    # Token window (~3 chars/token) on the kept text.
    if _estimate_chars(kept) > max_tokens:
        budget = max_tokens * 3
        kept_head, kept_tail = _head_tail_split(kept, budget)
        kept = kept_head + kept_tail

    kept_line_count = kept.count("\n") + (0 if kept.endswith("\n") or not kept else 1)
    omitted_lines = max(0, total_lines - kept_line_count)
    kept_bytes_len = len(kept.encode("utf-8"))

    notice = (
        f"\n\n[... Output truncated: showing head+tail ({kept_line_count} lines, "
        f"{kept_bytes_len} bytes) of {total_lines} total lines "
        f"({total_bytes} bytes). {omitted_lines} lines omitted in the middle ...]\n"
    )
    return kept + notice


async def bound_and_store(
    text: str,
    *,
    max_lines: int = 500,
    max_bytes: int = 100_000,
    max_tokens: int = 12_000,
) -> str:
    """Bound tool output; if oversized, spill full text to sandbox disk and reference path."""
    if not text:
        return text

    encoded = text.encode("utf-8")
    if (
        len(encoded) <= max_bytes
        and len(text.splitlines()) <= max_lines
        and _estimate_chars(text) <= max_tokens
    ):
        return text

    output_id = f"out_{uuid.uuid4().hex[:8]}"
    spill_path: str | None = None
    writer = _resolve_spill_writer()

    if writer is not None:
        try:
            spill_path = await writer(output_id, text)
        except Exception:
            logger.exception("Failed to write spilled tool output to sandbox workspace")

    bounded = bound_text(text, max_lines=max_lines, max_bytes=max_bytes, max_tokens=max_tokens)

    if spill_path:
        header = (
            f"[NOTE: Full output ({len(text.splitlines())} lines, {len(encoded)} bytes) "
            f"saved to sandbox file: {spill_path}. You can inspect it via grep/cat if needed.]\n\n"
        )
        return header + bounded

    return bounded
