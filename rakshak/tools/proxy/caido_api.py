"""Direct Caido GraphQL queries and helper methods."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

SortBy = Literal["timestamp", "id", "resp_code", "roundtrip"]
SortOrder = Literal["asc", "desc"]


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
    query GetRequests($filter: RequestFilter, $first: Int, $after: String, $sort: RequestSort) {
      requests(filter: $filter, first: $first, after: $after, sort: $sort) {
        edges {
          node {
            id
            method
            host
            path
            query
            response {
              statusCode
              roundtripTime
            }
            timestamp
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    variables: dict[str, Any] = {"first": first, "after": after}
    if httpql_filter:
        variables["filter"] = {"raw": httpql_filter}

    try:
        data = await client.execute_graphql(query, variables)
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
        data = await client.execute_graphql(query, {"id": request_id})
        return data.get("request") or {}
    except Exception as exc:
        return {"error": str(exc)}
