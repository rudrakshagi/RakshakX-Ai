"""Agent function tools for inspecting and replaying proxy traffic."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from agents import RunContextWrapper, function_tool

from rakshak.tools.proxy import caido_api

logger = logging.getLogger(__name__)

# All agents in a scan share one host-side Caido client whose GraphQL transport
# is not concurrency-safe (parallel calls raise "Transport is already connected").
# Serialize every host-side proxy call through this lock.
_CAIDO_CALL_LOCK = asyncio.Lock()


def _get_client(ctx: RunContextWrapper) -> Any | None:
    inner = ctx.context if isinstance(ctx.context, dict) else {}
    return inner.get("caido_client")


@function_tool(timeout=60)
async def list_requests(
    ctx: RunContextWrapper,
    httpql_filter: str | None = None,
    first: int = 30,
) -> str:
    """List captured HTTP requests from the Caido proxy with HTTPQL filtering.

    Examples of HTTPQL syntax:
    - resp.code.gte:400 (all error responses)
    - req.method.eq:"POST" (all POST requests)
    - req.path.cont:"/api" (all API paths)
    """
    client = _get_client(ctx)
    if client is None:
        return json.dumps({"success": False, "error": "Caido proxy client is not active in this session."})

    async with _CAIDO_CALL_LOCK:
        res = await caido_api.query_requests(client, httpql_filter=httpql_filter, first=first)

    return json.dumps({"success": True, "data": res}, ensure_ascii=False)


@function_tool(timeout=60)
async def view_request(
    ctx: RunContextWrapper,
    request_id: str,
) -> str:
    """Inspect full raw request and response headers and bodies for a captured request ID."""
    client = _get_client(ctx)
    if client is None:
        return json.dumps({"success": False, "error": "Caido proxy client is not active in this session."})

    async with _CAIDO_CALL_LOCK:
        res = await caido_api.get_request_details(client, request_id)

    return json.dumps({"success": True, "request": res}, ensure_ascii=False)
