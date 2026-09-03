"""Model configuration, provider adapters, and tool schema helpers."""

from __future__ import annotations

import logging
import os
from typing import Any

from agents.extensions.models.litellm_provider import LitellmProvider

logger = logging.getLogger(__name__)

OPCODE_BASE_URL = "https://opencode.ai/zen/v1"
_OPCODE_CLIENT_HEADER = "desktop"


def _is_opencode_free(settings: Any, model: str | None = None) -> bool:
    """Detect the no-auth OpenCode Free provider (alias `oc` / `opencode-free`)."""
    model = model or (getattr(getattr(settings, "llm", None), "model", None) or "")
    model_lower = model.lower()
    provider = str(getattr(getattr(settings, "llm", None), "provider", "") or "").lower()
    return (
        provider in ("opencode", "opencode-free", "opencode_free", "oc")
        or model_lower.startswith("openai/oc/")
        or model_lower.startswith("oc/")
    )


def _normalize_opencode_model(model: str | None) -> str:
    """Map an `oc/...` opencode-free model id to the openai-compatible id sent upstream."""
    if not model:
        return "muse-spark-1.3-contributor-free"
    if model.lower().startswith("openai/oc/"):
        return model[10:]
    if model.lower().startswith("oc/"):
        return model[3:]
    return model


def _resolve_api_key(settings: Any) -> str | None:
    """Resolve the provider API key from settings or standard env variables."""
    if settings and settings.llm.api_key:
        return str(settings.llm.api_key)
    model = (getattr(settings.llm, "model", "") or "").lower() if settings else ""
    if model.startswith("anthropic") or "claude" in model:
        return os.getenv("ANTHROPIC_API_KEY")
    if "gemini" in model or "google" in model:
        return os.getenv("GEMINI_API_KEY")
    if model.startswith("groq"):
        return os.getenv("GROQ_API_KEY")
    if model.startswith("openrouter"):
        return os.getenv("OPENROUTER_API_KEY")
    if model.startswith("ollama"):
        return "not-required"
    return os.getenv("OPENAI_API_KEY")


class RakshakProvider(LitellmProvider):
    """Provider wrapper adapting LiteLLM endpoints to the agent engine.

    Subclasses the openai-agents SDK's LitellmProvider so the Runner resolves
    model names like ``groq/openai/gpt-oss-120b`` through LiteLLM, which routes
    the request to any supported provider (Groq, OpenAI, Anthropic, Ollama...).
    """

    def __init__(self, settings: Any | None = None) -> None:
        from agents.extensions.models.litellm_model import LitellmModel

        self.settings = settings
        _set_provider_env(settings)
        is_opcode = _is_opencode_free(settings)

        def get_model(model_name: str | None) -> Any:
            model = model_name or "openai/gpt-4o"
            if is_opcode:
                model = "openai/" + _normalize_opencode_model(model)
                _configure_opencode_headers()
                base_url = OPCODE_BASE_URL
                return LitellmModel(model=model, base_url=base_url, api_key="dummy")
            api_key = _resolve_api_key(settings)
            api_base = getattr(getattr(settings, "llm", None), "api_base", None) if settings else None
            return LitellmModel(model=model, base_url=api_base, api_key=api_key) if api_key else LitellmModel(model=model, base_url=api_base)

        self._get_model = get_model

    def get_model(self, model_name: str | None) -> Any:
        return self._get_model(model_name)


def _set_provider_env(settings: Any) -> None:
    """Set the provider-specific API key env var from settings without overwriting existing values."""
    if not settings or not settings.llm.api_key:
        return
    model = (settings.llm.model or "").lower()
    key = settings.llm.api_key
    if model.startswith("anthropic") or "claude" in model:
        os.environ.setdefault("ANTHROPIC_API_KEY", key)
    elif "gemini" in model or "google" in model:
        os.environ.setdefault("GEMINI_API_KEY", key)
    elif model.startswith("groq"):
        os.environ.setdefault("GROQ_API_KEY", key)
    elif model.startswith("openrouter"):
        os.environ.setdefault("OPENROUTER_API_KEY", key)
    elif not model.startswith("ollama"):
        os.environ.setdefault("OPENAI_API_KEY", key)


def configure_model_defaults(settings: Any) -> None:
    """Set global LiteLLM parameters (drop params, telemetry flags, timeouts)."""
    try:
        import litellm
        litellm.drop_params = True
        litellm.telemetry = False
        litellm.request_timeout = settings.llm.timeout  # type: ignore[attr-defined]
        if _is_opencode_free(settings):
            _configure_opencode_headers()
            return
        api_key = _resolve_api_key(settings)
        if api_key:
            _set_provider_env(settings)
    except ImportError:
        pass


def _configure_opencode_headers() -> None:
    """Configure LiteLLM to talk to the no-auth OpenCode Free endpoint.

    The Zen gateway is ``noAuth``: it rejects a non-empty invalid ``Authorization``
    header but honours ``Authorization: `` (empty). LiteLLM's OpenAI provider demands
    a key value, so we supply a dummy key and override the header to empty while
    sending the ``x-opencode-client`` header the gateway expects.
    """
    try:
        import litellm
        litellm.headers = {  # type: ignore[assignment]
            "x-opencode-client": _OPCODE_CLIENT_HEADER,
            "Authorization": "",
        }
    except ImportError:
        pass


def uses_chat_completions_tool_schema(model_name: str, settings: Any) -> bool:
    """Check if the resolved model uses standard Chat Completions JSON schema tools."""
    model_lower = model_name.lower()
    return not (model_lower.startswith("openai/") or model_lower.startswith("gpt-") or model_lower.startswith("o1") or model_lower.startswith("o3"))
