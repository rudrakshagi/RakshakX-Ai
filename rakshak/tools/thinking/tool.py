"""Private scratchpad tool for agent cognitive reasoning."""

from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool


@function_tool(timeout=10)
async def think(ctx: RunContextWrapper, thought: Annotated[str, "Private reasoning or hypothesis to record."]) -> str:
    """Record a private reasoning note or hypothesis without modifying scan state.

    Use this to structure your next steps, analyze complex exploit responses,
    or deliberate on payload variations before executing them in the sandbox.
    """
    return json.dumps({
        "success": True,
        "status": "thought_recorded",
        "note": "Private reasoning recorded. Proceed with your planned actions.",
    })
