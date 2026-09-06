"""Direct Caido GraphQL queries and helper methods."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

SortBy = Literal["timestamp", "id", "resp_code", "roundtrip"]
SortOrder = Literal["asc", "desc"]

# query_requests sort keys -> real RequestResponseOrderBy enum values.
_SORT_TO_ORDER_BY: dict[str, str] = {
    "timestamp": "CREATED_AT",
    "id": "ID",
    "resp_code": "RESP_STATUS_CODE",
    "roundtrip": "RESP_ROUNDTRIP_TIME",
}


async def _execute_graphql(
    client: Any, query: str, variables: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute a raw GraphQL query against the Caido daemon.

    The installed SDK client exposes ``client.graphql.query`` (raw data
    payload); older code called a nonexistent ``client.execute_graphql``,
    which made EVERY proxy query tool fail live with AttributeError.
    A legacy ``execute_graphql`` attribute is still honored if present.
    """
    if client is None:
        raise RuntimeError("Caido client unavailable")
    legacy = getattr(client, "execute_graphql", None)
    if callable(legacy):
        data = await legacy(query, variables or {})
        return data if isinstance(data, dict) else {}
    graphql = getattr(client, "graphql", None)
    query_fn = getattr(graphql, "query", None) if graphql is not None else None
    if callable(query_fn):
        data = await query_fn(query, variables or {})
        return data if isinstance(data, dict) else {}
    raise RuntimeError(
        "Caido client supports neither graphql.query nor execute_graphql; "
        "proxy inspection unavailable"
    )


async def query_requests(
    client: Any,
    *,
    httpql_filter: str | None = None,
    first: int = 50,
    after: str | None = None,
    sort_by: SortBy = "timestamp",
    sort_order: SortOrder = "desc",
) -> dict[str, Any]:
    """Execute GraphQL query to fetch filtered HTTP requests from Caido."""
    if client is None:
        return {"items": [], "total": 0, "has_next_page": False}

    query = """
    query GetRequests($first: Int, $after: String, $filter: HTTPQLInput, $order: RequestResponseOrderInput) {
      requests(first: $first, after: $after, filter: $filter, order: $order) {
        edges {
          cursor
          node {
            id
            method
            host
            port
            path
            query
            isTls
            createdAt
            response {
              id
              statusCode
              roundtripTime
              length
              createdAt
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    variables: dict[str, Any] = {
        "first": first,
        "after": after,
        "filter": {"code": httpql_filter} if httpql_filter else None,
        "order": {
            "by": _SORT_TO_ORDER_BY.get(sort_by, "CREATED_AT"),
            "ordering": "ASC" if sort_order == "asc" else "DESC",
        },
    }

    try:
        data = await _execute_graphql(client, query, variables)
        reqs = data.get("requests", {})
        edges = reqs.get("edges", [])
        nodes = [e["node"] for e in edges if "node" in e]
        return {
            "items": nodes,
            "total": len(nodes),
            "has_next_page": reqs.get("pageInfo", {}).get("hasNextPage", False),
            "end_cursor": reqs.get("pageInfo", {}).get("endCursor"),
        }
    except Exception as exc:
        logger.exception("Failed to query Caido GraphQL requests: %s", exc)
        return {"error": str(exc), "items": []}


async def get_request_details(client: Any, request_id: str) -> dict[str, Any]:
    """Fetch raw HTTP request and response content for a specific captured item."""
    if client is None:
        return {"error": "Caido client unavailable"}

    query = """
    query GetRequestDetails($id: ID!) {
      request(id: $id) {
        id
        raw
        response {
          statusCode
          raw
          roundtripTime
        }
      }
    }
    """
    try:
        data = await _execute_graphql(client, query, {"id": request_id})
        return data.get("request") or {}
    except Exception as exc:
        return {"error": str(exc)}
