"""Unit tests for report usage hooks and budget enforcement."""

from __future__ import annotations

import pytest

from rakshak.core.hooks import (
    BudgetExceededError,
    ReportUsageHooks,
    recomputed_budget_flags,
)


def test_recomputed_budget_flags_none_budget():
    assert recomputed_budget_flags(50.0, None) == (False, False)
    assert recomputed_budget_flags(50.0, 0) == (False, False)
    assert recomputed_budget_flags(50.0, -5) == (False, False)


def test_recomputed_budget_flags_hit_budget():
    assert recomputed_budget_flags(10.0, 10.0) == (True, True)
    assert recomputed_budget_flags(11.0, 10.0) == (True, True)


def test_recomputed_budget_flags_reserve_at_90():
    # 9.0/10.0 = 90% -> reserve only
    assert recomputed_budget_flags(9.0, 10.0) == (False, True)
    assert recomputed_budget_flags(8.9, 10.0) == (False, False)


def test_on_turn_complete_tracks_tokens():
    hooks = ReportUsageHooks(model="openai/gpt-4o-mini", max_budget_usd=10.0, max_turns=150)

    class Usage:
        total_tokens = 1000
        prompt_tokens = 700
        completion_tokens = 300

    hooks.on_turn_complete(Usage())
    assert hooks.total_turns == 1
    assert hooks.total_cost_usd > 0


def test_on_turn_complete_max_turns_raises():
    hooks = ReportUsageHooks(model="openai/gpt-4o-mini", max_budget_usd=10.0, max_turns=2)
    hooks.on_turn_complete(None)
    hooks.on_turn_complete(None)
    with pytest.raises(BudgetExceededError):
        hooks.on_turn_complete(None)


def test_on_turn_complete_budget_raises():
    hooks = ReportUsageHooks(model="openai/gpt-4o-mini", max_budget_usd=0.0001, max_turns=150)

    class Usage:
        total_tokens = 100000
        prompt_tokens = 50000
        completion_tokens = 50000

    with pytest.raises(BudgetExceededError):
        hooks.on_turn_complete(Usage())


def test_extend_budget():
    hooks = ReportUsageHooks(model="openai/gpt-4o-mini", max_budget_usd=10.0)
    hooks.extend_budget(5.0)
    assert hooks.max_budget_usd == 15.0


def test_on_turn_complete_no_usage_no_cost():
    hooks = ReportUsageHooks(model="openai/gpt-4o-mini", max_budget_usd=10.0)
    hooks.on_turn_complete(None)
    assert hooks.total_cost_usd == 0.0
