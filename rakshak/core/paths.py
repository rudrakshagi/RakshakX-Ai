"""Filesystem path resolvers for scans, state, and artifacts."""

from __future__ import annotations

from pathlib import Path


def base_runs_dir() -> Path:
    """Return the base directory where all scan runs are stored."""
    return Path("rakshak_runs")


def run_dir_for(scan_id: str) -> Path:
    """Return the absolute path for a specific scan run directory."""
    return base_runs_dir() / scan_id


def runtime_state_dir(run_dir: Path) -> Path:
    """Return the state directory housing coordinator snapshots and DBs."""
    return run_dir / ".state"


def workspace_spill_dir(run_dir: Path) -> Path:
    """Return the directory inside the run where oversized tool outputs are saved."""
    return run_dir / "spill"


def reports_dir_for(run_dir: Path) -> Path:
    """Return the directory where generated SARIF, Markdown, and PDF reports reside."""
    return run_dir / "reports"
