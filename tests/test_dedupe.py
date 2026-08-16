"""Unit tests for finding deduplication and URL normalization."""

from rakshak.report.dedupe import compute_vulnerability_hash, normalize_endpoint


def test_normalize_endpoint_replaces_dynamic_ids():
    url1 = "https://api.target.local/v1/users/42/profile"
    url2 = "https://api.target.local/v1/users/999/profile"
    assert normalize_endpoint(url1) == normalize_endpoint(url2)
    assert normalize_endpoint(url1) == "api.target.local/v1/users/{id}/profile"


def test_normalize_endpoint_sorts_query_parameters():
    url1 = "https://target.local/search?b=2&a=1"
    url2 = "https://target.local/search?a=1&b=2"
    assert normalize_endpoint(url1) == normalize_endpoint(url2)


def test_vulnerability_hash_stable():
    h1 = compute_vulnerability_hash(
        category="SQL Injection",
        endpoint="https://target.local/api/items?id=1",
        cwe_id="CWE-89",
        title="SQLi in items endpoint",
    )
    h2 = compute_vulnerability_hash(
        category="SQL Injection",
        endpoint="https://target.local/api/items?id=2",
        cwe_id="CWE-89",
        title="SQLi in items endpoint",
    )
    # Different query parameter values on same structure produce same hash for dedup
    assert h1 == h2
