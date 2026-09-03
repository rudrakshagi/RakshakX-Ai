"""Unit tests for filesystem path resolvers."""

from __future__ import annotations

from pathlib import Path

from rakshak.core import paths
from rakshak.core.paths import reports_dir_for, run_dir_for, runtime_state_dir, workspace_spill_dir


def test_run_dir_for_joins_base(monkeypatch):
    monkeypatch.setattr(paths, "base_runs_dir", lambda: Path("/tmp/rakshak_runs"))
    assert run_dir_for("scan-abc") == Path("/tmp/rakshak_runs/scan-abc")


def test_runtime_state_dir(tmp_path):
    run = tmp_path / "run"
    assert runtime_state_dir(run) == run / ".state"


def test_workspace_spill_dir(tmp_path):
    run = tmp_path / "run"
    assert workspace_spill_dir(run) == run / "spill"


def test_reports_dir(tmp_path):
    run = tmp_path / "run"
    assert reports_dir_for(run) == run / "reports"
