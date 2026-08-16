"""Vulnerability finding deduplication engine."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlparse


def normalize_endpoint(url_or_path: str) -> str:
    """Normalize URLs by stripping trailing slashes, scheme, and variable IDs."""
    if not url_or_path:
        return ""
    parsed = urlparse(url_or_path)
    path = parsed.path.rstrip("/") or "/"
    # Replace numeric and UUID path segments with placeholder to group dynamic paths
    path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
    path = re.sub(r"/[0-9a-fA-F-]{36}(?=/|$)", "/{uuid}", path)

    # Sort query parameters
    query_params = sorted(parse_qsl(parsed.query))
    sorted_query = "&".join(f"{k}" for k, _ in query_params)

    host = parsed.netloc.lower()
    return f"{host}{path}?{sorted_query}" if sorted_query else f"{host}{path}"


def compute_vulnerability_hash(
    *,
    category: str,
    endpoint: str,
    cwe_id: str,
    title: str,
) -> str:
    """Generate a stable composite hash for deduplicating similar findings across agents."""
    norm_ep = normalize_endpoint(endpoint)
    norm_cat = category.strip().lower()
    norm_cwe = cwe_id.strip().upper()
    key = f"{norm_cat}|{norm_cwe}|{norm_ep}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
