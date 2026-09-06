"""Caido HTTP proxy initialization and SDK bootstrapping."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_LOGIN_MUTATION = "mutation { loginAsGuest { token { accessToken } } }"
_CREATE_MUTATION = (
    "mutation CreateProject($input: CreateProjectInput!) {"
    " createProject(input: $input) { project { id name } } }"
)
_RENAME_MUTATION = (
    "mutation RenameProject($id: ID!, $name: String!) {"
    " renameProject(id: $id, name: $name) { project { id name } } }"
)
_SELECT_MUTATION = (
    "mutation SelectProject($id: ID!) {"
    " selectProject(id: $id) { currentProject { project { id name } } } }"
)
_LIST_QUERY = "{ projects { id name } }"


async def _gql(
    client: httpx.AsyncClient, url: str, query: str,
    variables: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    res = await client.post(
        url,
        json={"query": query, **({"variables": variables} if variables else {})},
        headers=headers,
    )
    res.raise_for_status()
    data = res.json()
    if data.get("errors"):
        raise RuntimeError(f"Caido GraphQL error: {data['errors']}")
    return data.get("data") or {}


async def ensure_project(
    client: httpx.AsyncClient, graphql_url: str, token: str, project_name: str,
) -> str:
    """Create (or reuse) a temporary guest project and select it.

    Guest sessions cannot persist projects, and the intercept proxy 500s
    every request when no project repository exists — so this step is what
    actually makes forwarding work, not just the daemon being up.
    """
    existing = await _gql(client, graphql_url, _LIST_QUERY, token=token)
    projects = existing.get("projects") or []
    for proj in projects:
        if proj.get("name") == project_name:
            project_id = proj["id"]
            break
    else:
        if projects:
            # Guest sessions are limited to a single temporary project
            # (a second createProject → PermissionDenied). Reuse the
            # container's default project by renaming it to this scan.
            first_id = projects[0]["id"]
            renamed = await _gql(
                client, graphql_url, _RENAME_MUTATION,
                variables={"id": first_id, "name": project_name},
                token=token,
            )
            project = (renamed.get("renameProject") or {}).get("project")
            if not project:
                raise RuntimeError(f"Could not rename Caido project to {project_name!r}: {renamed}")
            project_id = project["id"]
        else:
            created = await _gql(
                client, graphql_url, _CREATE_MUTATION,
                variables={"input": {"name": project_name, "temporary": True}},
                token=token,
            )
            project = (created.get("createProject") or {}).get("project")
            if not project:
                raise RuntimeError(f"Could not create Caido project {project_name!r}: {created}")
            project_id = project["id"]
    await _gql(client, graphql_url, _SELECT_MUTATION,
               variables={"id": project_id}, token=token)
    logger.info("Caido project %r selected (%s)", project_name, project_id)
    return str(project_id)


async def guest_login(client: httpx.AsyncClient, graphql_url: str) -> str:
    """Log in as guest (instance runs with --allow-guests) and return a token."""
    data = await _gql(client, graphql_url, _LOGIN_MUTATION)
    token = ((data.get("loginAsGuest") or {}).get("token") or {}).get("accessToken")
    if not token:
        raise RuntimeError(f"Caido guest login failed: {data}")
    return str(token)


async def bootstrap_caido(
    host_port: int,
    *,
    project_name: str = "rakshak_scan",
    retries: int = 40,
    delay: float = 2.0,
    post_ready_retries: int = 3,
) -> Any:
    """Connect to in-container Caido GraphQL daemon, acquire token, and prepare project."""
    # NOTE: no trailing slash — /graphql/ serves the UI SPA (HTTP 200!) while
    # only /graphql is the real JSON API. Readiness must check content, not status.
    base_url = f"http://127.0.0.1:{host_port}"
    graphql_url = f"{base_url}/graphql"

    logger.info("Connecting to Caido proxy daemon at %s", graphql_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        ready = False
        for _attempt in range(1, retries + 1):
            try:
                res = await client.post(graphql_url, json={"query": "{ __typename }"})
                ctype = res.headers.get("content-type", "")
                if res.status_code == 200 and "application/json" in ctype and res.json().get("data"):
                    ready = True
                    break
                # Daemon responding but not fully up yet (e.g. mid-boot 502/503): back off.
                await asyncio.sleep(delay)
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(delay)
            except Exception:
                await asyncio.sleep(delay)

        if not ready:
            raise RuntimeError(f"Could not reach Caido proxy daemon at {graphql_url} after {retries} attempts.")

        # Post-readiness steps (login/project/SDK connect) used to run ONCE:
        # a single transient 502 here killed the proxy for the whole scan
        # ("proceeding with direct scanning"). Retry with backoff instead.
        last_err: Exception | None = None
        for attempt in range(1, post_ready_retries + 1):
            try:
                token = await guest_login(client, graphql_url)
                await ensure_project(client, graphql_url, token, project_name)
                return await _connect_sdk(base_url, token, project_name)
            except ImportError:
                logger.warning("caido-sdk-client package not installed; proxy tool queries will use direct HTTP fallback.")
                return None
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "Caido bootstrap attempt %d/%d failed (%s); backing off...",
                    attempt, post_ready_retries, str(exc)[:160],
                )
                await asyncio.sleep(delay * attempt)
        raise RuntimeError(
            f"Caido bootstrap failed after {post_ready_retries} attempts: {last_err}"
        )


async def _connect_sdk(base_url: str, token: str, project_name: str) -> Any:
    """Initialize Caido Python SDK Client with the guest token directly
    (no interactive device flow — connect() would hang waiting for approval)."""
    from caido_sdk_client import Client
    from caido_sdk_client.auth.types import TokenAuthOptions
    from caido_sdk_client.client import ConnectOptions
    caido_client = Client(url=base_url, auth=TokenAuthOptions(token=token))
    # ready=False: we already verified readiness above with raw
    # GraphQL; the SDK's own ready probe would just repeat it.
    # TokenAuthOptions authenticates directly (no device flow).
    await caido_client.connect(ConnectOptions(ready=False))
    logger.info("Caido SDK client successfully initialized for %s", project_name)
    return caido_client
