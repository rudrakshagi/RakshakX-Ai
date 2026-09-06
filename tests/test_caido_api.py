"""Unit tests for rakshak.tools.proxy.caido_api (mocked, no docker)."""

from __future__ import annotations

import pytest

from rakshak.tools.proxy import caido_api
from rakshak.tools.proxy.caido_api import (
    _execute_graphql,
    get_request_details,
    query_requests,
)

CANNED = {
    "requests": {
        "edges": [{"node": {"id": "1"}}],
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }
}


class _GraphqlStub:
    def __init__(self, payload=None, exc=None):
        self.payload = payload
        self.exc = exc
        self.calls: list[tuple[str, dict]] = []

    async def query(self, query, variables=None):
        self.calls.append((query, variables or {}))
        if self.exc is not None:
            raise self.exc
        return self.payload


class _ModernClient:
    def __init__(self, stub):
        self.graphql = stub


class _LegacyClient:
    """Only execute_graphql, no .graphql attribute."""

    def __init__(self, payload=None, exc=None):
        self._payload = payload
        self._exc = exc
        self.calls: list[tuple[str, dict]] = []

    async def execute_graphql(self, query, variables=None):
        self.calls.append((query, variables or {}))
        if self._exc is not None:
            raise self._exc
        return self._payload


class _BareClient:
    """Neither graphql.query nor execute_graphql."""


@pytest.mark.asyncio
async def test_execute_graphql_modern_path():
    stub = _GraphqlStub(payload=CANNED)
    client = _ModernClient(stub)
    data = await _execute_graphql(client, "q", {"a": 1})
    assert data == CANNED
    assert stub.calls and stub.calls[0][0] == "q"


@pytest.mark.asyncio
async def test_query_requests_modern_returns_items_total():
    stub = _GraphqlStub(payload=CANNED)
    res = await query_requests(_ModernClient(stub), first=5)
    assert res["items"] == [{"id": "1"}]
    assert res["total"] == 1
    assert res["has_next_page"] is False
    assert "error" not in res


@pytest.mark.asyncio
async def test_query_requests_legacy_client_still_works():
    res = await query_requests(_LegacyClient(payload=CANNED), first=5)
    assert res["items"] == [{"id": "1"}]
    assert res["total"] == 1
    assert "error" not in res


@pytest.mark.asyncio
async def test_query_requests_none_client_empty():
    res = await query_requests(None)
    assert res == {"items": [], "total": 0, "has_next_page": False}


@pytest.mark.asyncio
async def test_execute_graphql_bare_client_raises():
    with pytest.raises(RuntimeError):
        await _execute_graphql(_BareClient(), "q", {})


@pytest.mark.asyncio
async def test_execute_graphql_none_client_raises():
    with pytest.raises(RuntimeError):
        await _execute_graphql(None, "q", {})


@pytest.mark.asyncio
async def test_query_requests_bare_client_error_shape():
    res = await query_requests(_BareClient())
    assert res["items"] == []
    assert "error" in res


@pytest.mark.asyncio
async def test_get_request_details_happy_path():
    payload = {"request": {"id": "1", "raw": "GET / HTTP/1.1"}}
    res = await get_request_details(_ModernClient(_GraphqlStub(payload=payload)), "1")
    assert res == {"id": "1", "raw": "GET / HTTP/1.1"}


@pytest.mark.asyncio
async def test_get_request_details_error_path():
    res = await get_request_details(
        _ModernClient(_GraphqlStub(exc=RuntimeError("boom"))), "1"
    )
    assert res == {"error": "boom"}
    res_none = await get_request_details(None, "1")
    assert "error" in res_none
