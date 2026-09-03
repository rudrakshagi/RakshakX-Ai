"""Unit tests for compaction engine and token estimation."""

from __future__ import annotations

from litellm.exceptions import BadRequestError, ContextWindowExceededError

from rakshak.llm.compaction import (
    compute_max_history_tokens,
    estimate_tokens,
    is_context_overflow,
)


def test_is_context_overflow_true_badrequest():
    exc = BadRequestError(
        message="This model's maximum context length is 8192 tokens",
        response=None,
        llm_provider="test",
        model="test",
    )
    assert is_context_overflow(exc) is True


def test_is_context_overflow_rate_limit_false():
    exc = BadRequestError(
        message="Rate limit reached, too many requests",
        response=None,
        llm_provider="test",
        model="test",
    )
    assert is_context_overflow(exc) is False


def test_is_context_overflow_typed_exception_true():
    assert is_context_overflow(
        ContextWindowExceededError("window exceeded", model="test", llm_provider="test")
    ) is True


def test_is_context_overflow_unknown_false():
    """Some random exception should not be treated as overflow."""
    assert is_context_overflow(ValueError("boom")) is False


def _make_item(text: str, role: str = "user"):
    class _Item:
        def __init__(self) -> None:
            self.raw_item = {"role": role, "content": text}

    return _Item()


def test_estimate_tokens_single_item():
    items = [_make_item("a" * 300)]
    # 300 chars // 3 = 100
    assert estimate_tokens(items) == 100


def test_estimate_tokens_multiple_items():
    items = [_make_item("a" * 90), _make_item("b" * 90)]
    assert estimate_tokens(items) == 60


def test_estimate_tokens_empty():
    assert estimate_tokens([]) == 0


def test_compute_max_history_tokens_groq():
    assert compute_max_history_tokens("groq/llama-3-70b") == int(8000 * 0.55)


def test_compute_max_history_tokens_openai():
    assert compute_max_history_tokens("openai/gpt-4o") == int(128000 * 0.55)


def test_compute_max_history_tokens_unknown_default():
    assert compute_max_history_tokens("foo/bar") == int(32000 * 0.55)

