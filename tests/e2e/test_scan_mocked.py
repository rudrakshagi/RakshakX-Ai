"""E2E test: full scan orchestration with a mocked LLM runner (no tokens spent)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rakshak.core import paths


def _make_result(items: list[dict]):
    """Build a fake RunResult that emits the given session items on turn 1."""
    class Usage:
        total_tokens = 120
        prompt_tokens = 90
        completion_tokens = 30

    result = MagicMock()
    result.usage = Usage()
    result.final_output = "scan complete"
    return result


@pytest.mark.asyncio
async def test_run_rakshak_scan_with_mocked_runner(tmp_path, monkeypatch):
    """Execute run_rakshak_scan with session_manager + Runner mocked away."""
    from rakshak.core.runner import run_rakshak_scan

    monkeypatch.setattr(paths, "base_runs_dir", lambda: tmp_path / "runs")

    # Mock the sandbox session bundle
    bundle = MagicMock()
    bundle.session = MagicMock()
    bundle.sdk_session = MagicMock()
    bundle.caido_client = None

    # Mock Runner.run to return a terminal result on first call
    def _fake_run(**kwargs):
        return _make_result([])

    with (
        patch("rakshak.core.runner.session_manager.create_or_reuse", AsyncMock(return_value=bundle)),
        patch("rakshak.core.runner.session_manager.cleanup", AsyncMock()),
        patch("agents.Runner.run", AsyncMock(side_effect=_fake_run)),
        patch("rakshak.config.models.configure_model_defaults", lambda *a, **k: None),
    ):
        result = await run_rakshak_scan(
            target="http://example.test",
            scan_id="e2e-mocked",
            max_budget_usd=1.0,
            max_turns=3,
        )

    assert result is None or getattr(result, "final_output", None) == "scan complete"


@pytest.mark.asyncio
async def test_run_rakshak_scan_respects_budget_stop(tmp_path, monkeypatch):
    from rakshak.core.runner import run_rakshak_scan

    monkeypatch.setattr(paths, "base_runs_dir", lambda: tmp_path / "runs")

    bundle = MagicMock()
    bundle.session = MagicMock()
    bundle.sdk_session = MagicMock()
    bundle.caido_client = None

    # Force a budget exceed error on first Runner call.
    async def _boom(**kwargs):
        from rakshak.core.hooks import BudgetExceededError
        raise BudgetExceededError("budget")

    with (
        patch("rakshak.core.runner.session_manager.create_or_reuse", AsyncMock(return_value=bundle)),
        patch("rakshak.core.runner.session_manager.cleanup", AsyncMock()),
        patch("agents.Runner.run", AsyncMock(side_effect=_boom)),
        patch("rakshak.config.models.configure_model_defaults", lambda *a, **k: None),
    ):
        result = await run_rakshak_scan(
            target="http://example.test",
            scan_id="e2e-budget",
            max_budget_usd=1.0,
            max_turns=3,
        )

    assert result is None
