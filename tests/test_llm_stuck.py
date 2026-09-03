"""Unit tests for stuck detector."""

from __future__ import annotations

from rakshak.llm.stuck_detector import StuckDetector


def test_detects_repeated_tool_call():
    d = StuckDetector(window_size=5, threshold=3)
    assert d.record_tool_call("list_requests", {"first": 10}) is False
    assert d.record_tool_call("list_requests", {"first": 10}) is False
    assert d.record_tool_call("list_requests", {"first": 10}) is True


def test_no_false_positive_varied_calls():
    d = StuckDetector(window_size=5, threshold=3)
    assert d.record_tool_call("think", {"thought": "a"}) is False
    assert d.record_tool_call("create_todo", {"id": "1"}) is False
    assert d.record_tool_call("think", {"thought": "b"}) is False


def test_different_args_not_stuck():
    d = StuckDetector(window_size=5, threshold=3)
    d.record_tool_call("list_requests", {"first": 1})
    d.record_tool_call("list_requests", {"first": 2})
    d.record_tool_call("list_requests", {"first": 1})
    # Mixed args -> not stuck
    assert d.record_tool_call("list_requests", {"first": 5}) is False


def test_unknown_tool_detection():
    d = StuckDetector()
    assert d.record_unknown_tool() is False
    assert d.record_unknown_tool() is False
    assert d.record_unknown_tool() is True


def test_reset_unknown_count():
    d = StuckDetector()
    d.record_unknown_tool()
    d.record_unknown_tool()
    d.reset_unknown_count()
    assert d.record_unknown_tool() is False


def test_reset_clears_window():
    d = StuckDetector(window_size=5, threshold=3)
    # Build up 3 identical calls -> stuck
    d.record_tool_call("list_requests", {})
    d.record_tool_call("list_requests", {})
    assert d.record_tool_call("list_requests", {}) is True
    # Reset -> window empties, need 3 fresh identical calls again
    d.reset()
    d.record_tool_call("list_requests", {})
    d.record_tool_call("list_requests", {})
    assert d.record_tool_call("list_requests", {}) is True
