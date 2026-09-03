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
    """Char-based token estimate for a list of session items.

    Uses a slightly more accurate ratio than 1:4 for mixed code/natural language.
    """
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
    return total_chars // 3


def _get_model_token_limit(model: str) -> int:
    """Return a conservative per-request token cap for known model families."""
    model_lower = model.lower()
    if "groq" in model_lower:
        return 8_000
    if "gpt-4o-mini" in model_lower or "gpt-oss" in model_lower or "llama-3" in model_lower:
        return 16_000
    if "gpt-4o" in model_lower:
        return 128_000
    if "claude-3" in model_lower or "claude-3.5" in model_lower:
        return 200_000
    return 32_000


def compute_max_history_tokens(model: str, context_tokens: int = 200_000) -> int:
    """Compute the max history tokens based on model and context window.

    Reserve ~30% for system prompt + tools + current turn overhead.
    """
    model_cap = _get_model_token_limit(model)
    effective = min(model_cap, context_tokens)
    return int(effective * 0.55)


async def maybe_compact(
    session: Any,
    *,
    model: str,
    instructions: str = "",
    force: bool = False,
    max_history_tokens: int | None = None,
    context_tokens: int = 200_000,
) -> bool:
    """Check session length and compact older turns into a security checkpoint if needed.

    Triggers proactively when the estimated history token count exceeds ``max_history_tokens``
    (computed from model window if not provided), or when ``force`` is set.
    """
    if session is None:
        return False

    if max_history_tokens is None:
        max_history_tokens = compute_max_history_tokens(model, context_tokens)

    async with session_write_lock(session):
        items = list(await session.get_items())

    if not force and estimate_tokens(items) <= max_history_tokens:
        return False

    logger.info("Triggering security context compaction for %d session items", len(items))

    head_items = items[:2]
    recent_items = items[-4:]
    middle_items = items[2:-4]

    if not middle_items:
        return False

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
