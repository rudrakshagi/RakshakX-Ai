"""Tool output bounding and sandbox spillage store."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

# Directory inside the sandbox container workspace where spilled tool outputs land
WORKSPACE_SPILL_DIR = "/workspace/.rakshak/spill"

# Callback registered by the scan runner to stream oversized output to the sandbox filesystem
SpillWriter = Callable[[str, str], Awaitable[str | None]]
_spill_writer: SpillWriter | None = None


def configure_spill_writer(writer: SpillWriter | None) -> None:
    """Register or clear the active sandbox file spill writer."""
    global _spill_writer  # noqa: PLW0603
    _spill_writer = writer


def _estimate_chars(text: str) -> int:
    """Rough char-based token estimate (1 token ~= 3 chars for mixed code/text)."""
    return len(text) // 3


def bound_text(
    text: str,
    *,
    max_lines: int = 500,
    max_bytes: int = 100_000,
    max_tokens: int = 12_000,
) -> str:
    """Truncate text exceeding line, byte, or token ceilings with a clean marker."""
    if not text:
        return text

    encoded = text.encode("utf-8")
    is_byte_capped = len(encoded) > max_bytes
    is_token_capped = _estimate_chars(text) > max_tokens
    lines = text.splitlines(keepends=True)
    is_line_capped = len(lines) > max_lines

    if not is_byte_capped and not is_line_capped and not is_token_capped:
        return text

    # Truncate by lines first
    kept_lines = lines[:max_lines]
    truncated_str = "".join(kept_lines)

    # Check byte cap on the remaining string
    if len(truncated_str.encode("utf-8")) > max_bytes:
        truncated_bytes = truncated_str.encode("utf-8")[:max_bytes]
        truncated_str = truncated_bytes.decode("utf-8", errors="ignore")

    # Check token cap on the remaining string
    if _estimate_chars(truncated_str) > max_tokens:
        truncated_chars = max_tokens * 3
        truncated_str = truncated_str[:truncated_chars]

    total_lines = len(lines)
    remaining_lines = max(0, total_lines - max_lines)

    notice = (
        f"\n\n[... Output truncated: showing first {min(len(kept_lines), max_lines)} lines "
        f"({len(truncated_str.encode('utf-8'))} bytes) of {total_lines} total lines "
        f"({len(encoded)} bytes). {remaining_lines} lines omitted ...]\n"
    )
    return truncated_str + notice


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

    if _spill_writer is not None:
        try:
            spill_path = await _spill_writer(output_id, text)
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
