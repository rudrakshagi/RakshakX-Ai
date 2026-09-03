"""Sliding-window stuck/repetition detector for agent tool-calling loops."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

_WINDOW_SIZE = 5
_REPEAT_THRESHOLD = 3


def _hash_tool_call(tool_name: str, arguments: Any) -> str:
    """Deterministic hash of a tool invocation for repeat detection."""
    key = f"{tool_name}:{json.dumps(arguments, sort_keys=True, default=str)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class StuckDetector:
    """Detects repeated tool calls in a sliding window to break infinite loops."""

    def __init__(self, window_size: int = _WINDOW_SIZE, threshold: int = _REPEAT_THRESHOLD) -> None:
        self._window: deque[str] = deque(maxlen=window_size)
        self._threshold = threshold
        self._consecutive_unknown = 0

    def record_tool_call(self, tool_name: str, arguments: Any) -> bool:
        """Record a tool call and return True if the agent appears stuck."""
        h = _hash_tool_call(tool_name, arguments)
        self._window.append(h)

        if len(self._window) >= self._threshold:
            recent = list(self._window)[-self._threshold :]
            if len(set(recent)) == 1:
                logger.warning(
                    "Stuck detector: tool '%s' repeated %d times consecutively. Agent is stuck.",
                    tool_name,
                    self._threshold,
                )
                return True
        return False

    def record_unknown_tool(self) -> bool:
        """Track consecutive unknown-tool errors; return True if hallucination loop detected."""
        self._consecutive_unknown += 1
        if self._consecutive_unknown >= 3:
            logger.warning(
                "Stuck detector: %d consecutive unknown-tool errors. Model is hallucinating tools.",
                self._consecutive_unknown,
            )
            return True
        return False

    def reset_unknown_count(self) -> None:
        self._consecutive_unknown = 0

    def reset(self) -> None:
        self._window.clear()
        self._consecutive_unknown = 0
