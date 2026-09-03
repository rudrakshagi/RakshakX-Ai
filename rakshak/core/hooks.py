"""Lifecycle usage hooks, token budgeting, and cost enforcement."""

from __future__ import annotations

import logging
from typing import Any

from agents.exceptions import AgentsException

logger = logging.getLogger(__name__)

LLM_TURN_KEY = "llm_turn"

_MODEL_COST_PER_1K: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-5": (0.0025, 0.01),
    "claude-3-opus": (0.015, 0.075),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-haiku": (0.00025, 0.00125),
    "claude-3.5-sonnet": (0.003, 0.015),
    "claude-3.5-haiku": (0.0008, 0.004),
    "o1": (0.015, 0.06),
    "o3": (0.01, 0.04),
    "o3-mini": (0.0011, 0.0044),
    "o4-mini": (0.0011, 0.0044),
}


def _estimate_model_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost using model-specific pricing tiers."""
    model_lower = model.lower()

    for pattern, (prompt_price, completion_price) in _MODEL_COST_PER_1K.items():
        if pattern in model_lower:
            return (prompt_tokens / 1000.0) * prompt_price + (completion_tokens / 1000.0) * completion_price

    if "groq" in model_lower:
        return (prompt_tokens / 1000.0) * 0.0001 + (completion_tokens / 1000.0) * 0.0001

    return (prompt_tokens / 1000.0) * 0.005 + (completion_tokens / 1000.0) * 0.015


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
        if usage and hasattr(usage, "total_tokens"):
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            logger.info(
                "Turn tokens: prompt=%s completion=%s (total=%s)",
                prompt_tokens,
                completion_tokens,
                usage.total_tokens,
            )
            estimated_cost = _estimate_model_cost(self.model, prompt_tokens, completion_tokens)
            self.total_cost_usd += estimated_cost

        if self.total_turns > self.max_turns:
            raise BudgetExceededError(f"Exceeded max allowed turns ({self.max_turns}) for this scan.")

        budget_stopped, _ = recomputed_budget_flags(
            self.total_cost_usd,
            self.max_budget_usd,
            interactive=self.interactive,
        )
        if budget_stopped:
            raise BudgetExceededError(
                f"Scan reached dollar budget limit (${self.total_cost_usd:.2f} >= ${self.max_budget_usd:.2f})"
            )
