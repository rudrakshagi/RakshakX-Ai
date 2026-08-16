"""Caido HTTP proxy initialization and SDK bootstrapping."""

from __future__ import annotations

import asyncio
import logging
import httpx
from typing import Any

logger = logging.getLogger(__name__)


async def bootstrap_caido(
    host_port: int,
    *,
    project_name: str = "rakshak_scan",
    retries: int = 15,
    delay: float = 1.0,
) -> Any:
    """Connect to in-container Caido GraphQL daemon, acquire token, and prepare project."""
    base_url = f"http://127.0.0.1:{host_port}"
    graphql_url = f"{base_url}/graphql/"

    logger.info("Connecting to Caido proxy daemon at %s", graphql_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        ready = False
        for attempt in range(1, retries + 1):
            try:
                res = await client.post(
                    graphql_url,
                    json={"query": "{ viewer { id } }"},
                )
                if res.status_code in (200, 400):
                    ready = True
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(delay)

        if not ready:
            raise RuntimeError(f"Could not reach Caido proxy daemon at {graphql_url} after {retries} attempts.")

        # Initialize Caido Python SDK Client
        try:
            from caido_sdk_client import Client
            caido_client = Client(url=base_url)
            logger.info("Caido SDK client successfully initialized for %s", project_name)
            return caido_client
        except ImportError:
            logger.warning("caido-sdk-client package not installed; proxy tool queries will use direct HTTP fallback.")
            return None
