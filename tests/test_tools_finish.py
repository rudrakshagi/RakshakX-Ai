"""Unit tests for finish_scan lifecycle tool."""

from __future__ import annotations

import asyncio
import json

from rakshak.report.state import ReportState, set_global_report_state
from rakshak.tools.finish.tool import finish_scan
from tests.conftest import invoke_tool


def test_finish_scan_root_guard():
    # Root agent has parent_id None; a child has parent_id set.
    res = asyncio.run(invoke_tool(
        finish_scan,
        {"parent_id": "parent01"},
        executive_summary="s",
        methodology="m",
        technical_analysis="t",
        recommendations="r",
    ))
    payload = json.loads(res)
    assert payload["success"] is False
    assert "only" in payload["error"]


def test_finish_scan_validation_empty():
    res = asyncio.run(invoke_tool(
        finish_scan,
        {"parent_id": None},
        executive_summary="",
        methodology="",
        technical_analysis="",
        recommendations="",
    ))
    payload = json.loads(res)
    assert payload["success"] is False
    assert payload["error"] == "Validation failed"


def test_finish_scan_success(tmp_path):
    scan_id = "scan-test"
    state = ReportState(scan_id=scan_id, run_dir=tmp_path / "run")
    set_global_report_state(state)

    res = asyncio.run(invoke_tool(
        finish_scan,
        {"parent_id": None},
        executive_summary="summary",
        methodology="meth",
        technical_analysis="tech",
        recommendations="rec",
    ))
    payload = json.loads(res)
    assert payload["success"] is True
    assert payload["scan_completed"] is True
    assert state.executive_summary == "summary"
