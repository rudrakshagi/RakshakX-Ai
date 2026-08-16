"""Model configuration, provider adapters, and tool schema helpers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RakshakProvider:
    """Provider wrapper adapting LiteLLM endpoints to the agent engine."""

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings


def configure_model_defaults(settings: Any) -> None:
    """Set global LiteLLM parameters (drop params, telemetry flags, timeouts)."""
    try:
        import litellm
        litellm.drop_params = True
        litellm.telemetry = False
        litellm.request_timeout = settings.llm.timeout
    except ImportError:
        pass


def uses_chat_completions_tool_schema(model_name: str, settings: Any) -> bool:
    """Check if the resolved model uses standard Chat Completions JSON schema tools."""
    model_lower = model_name.lower()
    if (
        model_lower.startswith("openai/")
        or model_lower.startswith("gpt-")
        or model_lower.startswith("o1")
        or model_lower.startswith("o3")
    ):
        return False
    return True
