"""Configuration settings for RakshakX engine."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_TURNS: int = 150
DEFAULT_SANDBOX_IMAGE: str = "rakshakx/sandbox:latest"


class LLMSettings(BaseModel):
    """Configuration for LLM models and API parameters."""
    provider: str | None = Field(
        default=None,
        description="Provider identifier (e.g. opencode-free, openrouter, groq, ollama, openai).",
    )
    model: str = Field(
        default="openai/gpt-5.4",
        description="LLM identifier compatible with LiteLLM (e.g. openai/gpt-5.4, anthropic/claude-3-7-sonnet)",
    )
    api_key: str | None = Field(
        default=None,
        description="Direct API key override; fallback to standard env variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)",
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base endpoint URL",
    )
    timeout: float = Field(
        default=180.0,
        description="Maximum seconds to wait for model completion before timeout",
    )
    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default="medium",
        description="Reasoning effort tier for reasoning models (e.g. o1, o3, o3-mini)",
    )
    temperature: float | None = Field(
        default=None,
        description="Sampling temperature override (0.0-2.0)",
    )
    force_required_tool_choice: bool = Field(
        default=False,
        description="Force the model to make at least one tool call on every turn",
    )
    prompt_cache: bool = Field(
        default=True,
        description="Enable prompt caching where supported by the provider",
    )
    extra_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers sent with every LLM completion request",
    )


class ContextSettings(BaseModel):
    """Token limits, output capping, and compaction thresholds."""
    max_context_tokens: int = Field(
        default=200_000,
        description="Maximum context window ceiling before compaction is forced",
    )
    tool_output_max_lines: int = Field(
        default=500,
        description="Max lines returned directly in tool result before spilling to disk",
    )
    tool_output_max_bytes: int = Field(
        default=100_000,
        description="Max raw byte size returned in tool result (approx 100KB)",
    )
    tool_output_max_tokens: int = Field(
        default=12_000,
        description="Max tokens allowed per individual tool output before bounding",
    )


class RuntimeSettings(BaseModel):
    """Container sandbox and local execution settings."""
    docker_image: str = Field(
        default=DEFAULT_SANDBOX_IMAGE,
        description="Docker image used to instantiate the pentesting sandbox",
    )
    runs_dir: Path = Field(
        default=Path("rakshak_runs"),
        description="Root directory where scan states, logs, and artifacts are persisted",
    )
    max_context_images: int = Field(
        default=5,
        description="Maximum screenshot images retained in active agent context",
    )
    enable_caido: bool = Field(
        default=True,
        description="Whether to boot and route traffic through the Caido proxy sidecar",
    )


class RakshakSettings(BaseSettings):
    """Master application settings."""
    model_config = SettingsConfigDict(
        env_prefix="RAKSHAK_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    context: ContextSettings = Field(default_factory=ContextSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    max_budget_usd: float = Field(
        default=10.0,
        description="Maximum budget in USD for the entire scan",
    )


_GLOBAL_SETTINGS: RakshakSettings | None = None


def get_settings() -> RakshakSettings:
    """Return the cached global settings instance or load a new one."""
    global _GLOBAL_SETTINGS  # noqa: PLW0603
    if _GLOBAL_SETTINGS is None:
        _GLOBAL_SETTINGS = RakshakSettings()
    return _GLOBAL_SETTINGS


def load_settings() -> RakshakSettings:
    """Return the cached global settings instance or load a new one with config overrides."""
    global _GLOBAL_SETTINGS  # noqa: PLW0603
    if _GLOBAL_SETTINGS is None:
        import json
        settings = RakshakSettings()

        config_path = Path(".rakshakx") / "config.json"
        legacy_path = Path("rakshak.config.json")
        config_file = config_path if config_path.exists() else (legacy_path if legacy_path.exists() else None)

        if config_file:
            try:
                cfg = json.loads(config_file.read_text(encoding="utf-8"))
                if cfg.get("provider"):
                    settings.llm.provider = cfg["provider"]
                if cfg.get("model"):
                    settings.llm.model = cfg["model"]
                if cfg.get("api_key"):
                    settings.llm.api_key = cfg["api_key"]
                if cfg.get("api_base"):
                    settings.llm.api_base = cfg["api_base"]
                if cfg.get("temperature") is not None:
                    settings.llm.temperature = cfg["temperature"]
                if cfg.get("max_budget_usd") is not None:
                    settings.max_budget_usd = cfg["max_budget_usd"]
            except Exception:
                pass
        _GLOBAL_SETTINGS = settings
    return _GLOBAL_SETTINGS
