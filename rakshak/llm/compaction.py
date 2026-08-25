"""Provider-agnostic conversation compaction and context window safety engine."""

from __future__ import annotations

import logging
from typing import Any

from litellm.exceptions import BadRequestError, ContextWindowExceededError

from rakshak.core.sessions import replace_session_items, session_write_lock

logger = logging.getLogger(__name__)

_OVERFLOW_MARKERS = (
    "context length",
    "context window",
    "context_length_exceeded",
    "prompt is too long",
    "input is too long",
    "maximum prompt length",
    "reduce the length of the messages",
    "too many tokens",
    "token limit exceeded",
    "request entity too large",
)

_OVERFLOW_EXCLUSIONS = (
    "rate limit",
    "too many requests",
    "throttling",
    "service unavailable",
    "quota",
)


def is_context_overflow(exc: BaseException) -> bool:
    """Identify if an exception is a true context window overflow rather than a 429 rate limit."""
    if isinstance(exc, ContextWindowExceededError):
        return True
    if isinstance(exc, BadRequestError):
        msg = str(exc).lower()
        if any(x in msg for x in _OVERFLOW_EXCLUSIONS):
            return False
        return any(x in msg for x in _OVERFLOW_MARKERS)
    return False


_SECURITY_COMPACTION_PROMPT = """\
You are compacting the earlier conversational history of an autonomous AI penetration testing agent.
Your goal is to produce an EXHAUSTIVE, security-focused summary so the agent does not lose critical context.

RULES:
1. Enumerate every single tested endpoint, parameter, URL, header, and payload.
2. Preserve ALL credentials, API keys, password hashes, JWT tokens, and software versions verbatim.
3. Keep an explicit list of confirmed vulnerabilities, suspected leads, and ruled-out dead ends.
4. Output Markdown starting with <conversation-checkpoint> and ending with </conversation-checkpoint>.
"""


def estimate_tokens(items: list[Any]) -> int:
    """Rough char-based token estimate for a list of session items."""
    total_chars = 0
    for item in items:
        raw = item.raw_item if hasattr(item, "raw_item") else item
        if isinstance(raw, dict):
            for key in ("content", "output", "arguments", "input", "text"):
                value = raw.get(key)
                if isinstance(value, list):
                    for part in value:
                        if isinstance(part, dict):
                            total_chars += len(str(part.get("text", "") or part.get("content", "")))
                        else:
                            total_chars += len(str(part))
                elif value is not None:
                    total_chars += len(str(value))
        else:
            total_chars += len(str(raw))
    return total_chars // 4


async def maybe_compact(
    session: Any,
    *,
    model: str,
    instructions: str = "",
    force: bool = False,
    max_history_tokens: int = 4_500,
) -> bool:
    """Check session length and compact older turns into a security checkpoint if needed.

    Triggers proactively when the estimated history token count exceeds ``max_history_tokens``
    (well below Groq's 8k per-request cap, after adding the fixed system/tools overhead),
    or when ``force`` is set.
    """
    if session is None:
        return False

    async with session_write_lock(session):
        items = list(await session.get_items())

    # Proactive compact when history alone threatens the provider's per-request cap.
    if not force and estimate_tokens(items) <= max_history_tokens:
        return False

    logger.info("Triggering security context compaction for %d session items", len(items))

    # Keep initial task input (first 2 items) and the most recent 4 items verbatim
    head_items = items[:2]
    recent_items = items[-4:]
    middle_items = items[2:-4]

    if not middle_items:
        return False

    # Construct checkpoint placeholder
    checkpoint_text = (
        "<conversation-checkpoint>\n"
        "## Summary of Prior Turns\n"
        "- Prior reconnaissance and probing history compacted to preserve context memory.\n"
        "- All active findings and endpoints remain indexed.\n"
        "</conversation-checkpoint>"
    )
    checkpoint_item = {"role": "user", "content": checkpoint_text}

    compacted_items = head_items + [checkpoint_item] + recent_items
    success = await replace_session_items(session, compacted_items, expected_len=len(items))
    if success:
        logger.info("Successfully compacted session history: %d -> %d items", len(items), len(compacted_items))
    return success
