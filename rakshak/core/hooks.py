"""Lifecycle usage hooks, token budgeting, and cost enforcement."""

from __future__ import annotations

import logging
from typing import Any

from agents.exceptions import AgentsException

logger = logging.getLogger(__name__)

LLM_TURN_KEY = "llm_turn"


class BudgetExceededError(AgentsException):
    """Raised when the total LLM cost exceeds the hard scan ceiling."""


class BudgetPausedError(AgentsException):
    """Raised in interactive mode when spending hits the warning threshold."""


class SubagentBudgetReservedError(AgentsException):
    """Raised to park subagents and reserve remaining tokens for root executive reporting."""


def recomputed_budget_flags(
    total_cost_usd: float,
    max_budget_usd: float | None,
    *,
    interactive: bool = False,
) -> tuple[bool, bool]:
    """Compute (budget_stopped, reserve_stopped) based on current spend vs budget."""
    if max_budget_usd is None or max_budget_usd <= 0:
        return False, False

    if total_cost_usd >= max_budget_usd:
        return True, True

    # When spend reaches 90% of budget, trigger reserve stop so subagents wrap up
    # and save the final 10% for the root agent's finish_scan report
    if total_cost_usd >= (max_budget_usd * 0.9):
        return False, True

    return False, False


class ReportUsageHooks:
    """Agent lifecycle hook tracking token usage and enforcing spend limits."""

    def __init__(
        self,
        *,
        model: str,
        max_budget_usd: float | None = None,
        max_turns: int = 150,
        interactive: bool = False,
    ) -> None:
        self.model = model
        self.max_budget_usd = max_budget_usd
        self.max_turns = max_turns
        self.interactive = interactive
        self.total_turns = 0
        self.total_cost_usd = 0.0

    def extend_budget(self, additional_usd: float = 5.0) -> None:
        """Allow human operator to top up the scan budget during interactive execution."""
        if self.max_budget_usd is not None:
            self.max_budget_usd += additional_usd
            logger.info("Extended scan budget by $%.2f -> new ceiling: $%.2f", additional_usd, self.max_budget_usd)

    def on_turn_complete(self, usage: Any) -> None:
        """Process turn token usage and verify against budget ceilings."""
        self.total_turns += 1
        if self.total_turns > self.max_turns:
            raise BudgetExceededError(f"Exceeded max allowed turns ({self.max_turns}) for this scan.")

        # Estimate cost based on model pricing if usage stats available
        if usage and hasattr(usage, "total_tokens"):
            # Placeholder conservative estimate: ~$0.005 per 1k tokens average
            estimated_cost = (usage.total_tokens / 1000.0) * 0.005
            self.total_cost_usd += estimated_cost

        budget_stopped, _ = recomputed_budget_flags(
            self.total_cost_usd,
            self.max_budget_usd,
            interactive=self.interactive,
        )
        if budget_stopped:
            raise BudgetExceededError(
                f"Scan reached dollar budget limit (${self.total_cost_usd:.2f} >= ${self.max_budget_usd:.2f})"
            )
