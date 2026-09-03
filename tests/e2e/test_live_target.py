"""Opt-in live vulnerable-target E2E (spends real LLM tokens).

Skipped by default. To run (requires Docker daemon + model API key):

    pytest tests/e2e/test_live_target.py --run-live -v
"""

from __future__ import annotations

import pytest

from rakshak.core.paths import run_dir_for

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_live_scan_end_to_end(tmp_path, monkeypatch, run_live: bool):
    if not run_live:
        pytest.skip("Live scan disabled; pass --run-live to enable")

    from rakshak.core import paths
    from rakshak.core.runner import run_rakshak_scan

    monkeypatch.setattr(paths, "base_runs_dir", lambda: tmp_path / "runs")

    result = await run_rakshak_scan(
        target="http://172.17.0.1:3001",
        scan_id="e2e-live",
        scan_mode="quick",
        max_budget_usd=2.0,
        max_turns=5,
    )

    run_dir = run_dir_for("e2e-live")
    assert run_dir.exists()
    assert (run_dir / ".state").exists()
    assert result is None or getattr(result, "final_output", None) is not None
