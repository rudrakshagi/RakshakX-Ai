"""Model-friendly tool error hooks for the agents SDK.

The SDK's default failure path returns either a generic message or the raw
exception text to the model ("An error occurred... Error: <traceback-ish>"),
which wastes turns: the model retries the same bad call instead of fixing
it. These hooks (wired via ``failure_error_function`` / ``timeout_error_function``
on every ``@function_tool``) return the house ``{"success": False, ...}``
envelope with a one-line cause plus an actionable hint, so one failed call
teaches the model what to do next.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# (exception-type substring match, hint) — first match wins. Order matters:
# specific transport/shape errors before the generic fallback.
_HINT_RULES: tuple[tuple[str, str], ...] = (
    ("timed out", "The operation took too long. Re-run NARROWER (fewer targets, smaller wordlist, tighter filter) — do NOT repeat the identical call."),
    ("timeout", "The operation took too long. Re-run NARROWER (fewer targets, smaller wordlist, tighter filter) — do NOT repeat the identical call."),
    ("transport is already connected", "Proxy client was busy with a parallel call. Wait a moment and retry the same call once."),
    ("connection refused", "Target/proxy refused the connection — it may be down or still booting. Verify it is up, then retry."),
    ("connecterror", "Could not reach the target/proxy. Check the host/port is correct and the service is up, then retry."),
    ("name or service not known", "DNS failed for the hostname. Check the spelling/scope and retry with a resolvable target."),
    ("no such file", "Path does not exist. List the parent directory first, then retry with a correct path."),
    ("filenotfounderror", "Path does not exist. List the parent directory first, then retry with a correct path."),
    ("permissiondenied", "Permission denied. Retry with an allowed path/user or drop the privileged operation."),
    ("permission denied", "Permission denied. Retry with an allowed path/user or drop the privileged operation."),
    ("target agent", "The agent ID is wrong or the agent already finished. Call view_agent_graph for live IDs, then retry."),
    ("not found", "The referenced object does not exist. Re-list (agents/notes/todos/requests) for a live ID, then retry."),
    ("missing", "A required argument is missing. Re-read the tool description and retry with all required fields filled."),
    ("invalid", "An argument value is invalid. Re-read the tool description for the expected shape/range and retry corrected."),
    ("validation", "Arguments failed validation. Re-read the tool description for expected types/ranges and retry corrected."),
    ("unexpected keyword", "Unknown argument name. Re-read the tool description and retry using only documented parameters."),
)


def _match_hint(error_text: str) -> str:
    lowered = error_text.lower()
    for marker, hint in _HINT_RULES:
        if marker in lowered:
            return hint
    return "Fix the flagged problem and retry with corrected arguments; re-read the tool description first."


def _one_line(text: str, limit: int = 300) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "..."


def model_failure_message(ctx: Any, error: Exception) -> str:
    """failure_error_function: unhandled tool crash -> actionable JSON for the model."""
    try:
        cause = _one_line(f"{type(error).__name__}: {error}")
    except Exception:
        cause = "Unknown tool error"
    hint = _match_hint(cause)
    logger.warning("Tool failure surfaced to model: %s", cause)
    return json.dumps({"success": False, "error": cause, "hint": hint})


def model_timeout_message(ctx: Any, error: Exception) -> str:
    """timeout_error_function: tool timeout -> narrow-down guidance for the model."""
    try:
        cause = _one_line(f"{type(error).__name__}: {error}")
    except Exception:
        cause = "Tool timed out"
    return json.dumps({
        "success": False,
        "error": cause or "Tool timed out",
        "hint": "The operation exceeded its time budget. Re-run NARROWER (fewer targets, smaller wordlist, tighter filter) — do NOT repeat the identical call.",
    })


def is_timeout_error(error: BaseException) -> bool:
    """True for error types the timeout hook is meant to translate."""
    return isinstance(error, (asyncio.TimeoutError, TimeoutError))
