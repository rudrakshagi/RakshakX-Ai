"""Canonical severity normalization for findings, reports, and scoring.

The same severity string is compared in 5+ places (report state, PDF
counts, SARIF levels, benchmark adapters, viewer summary) — each with its
own ad-hoc ``.lower()`` or even exact-match comparison. Result: "Critical"
vs "critical" vs "none" vs "" silently fell out of counts, SARIF levels,
and report headers. Every producer/consumer must go through
:func:`normalize_severity` so "NONE", " None ", "info", "" all land on one
canonical value instead of leaking into reports as distinct buckets.
"""

from __future__ import annotations

CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"
INFORMATIONAL = "informational"

CANONICAL_SEVERITIES: tuple[str, ...] = (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)

_SEVERITY_RANK: dict[str, int] = {
    INFORMATIONAL: 0,
    LOW: 1,
    MEDIUM: 2,
    HIGH: 3,
    CRITICAL: 4,
}

_ALIASES: dict[str, str] = {
    "crit": CRITICAL,
    "moderate": MEDIUM,
    "med": MEDIUM,
    "none": INFORMATIONAL,  # CVSS 0.0 — informational, not a distinct bucket
    "info": INFORMATIONAL,
    "informative": INFORMATIONAL,
    "unknown": INFORMATIONAL,
    "n/a": INFORMATIONAL,
    "na": INFORMATIONAL,
    "": INFORMATIONAL,
}


def normalize_severity(value: object) -> str:
    """Map any severity-ish input to a canonical lowercase severity.

    Never raises, never returns empty: unknown/blank values become
    "informational" so findings are never silently dropped from counts.
    """
    try:
        key = str(value or "").strip().lower()
    except Exception:
        return INFORMATIONAL
    if key in _SEVERITY_RANK:
        return key
    return _ALIASES.get(key, INFORMATIONAL)


def severity_rank(value: object) -> int:
    """Numeric rank for ordering (critical=4 ... informational=0)."""
    return _SEVERITY_RANK[normalize_severity(value)]


def is_actionable(value: object) -> bool:
    """True for severities that represent real risk (low and above)."""
    return severity_rank(value) >= _SEVERITY_RANK[LOW]
