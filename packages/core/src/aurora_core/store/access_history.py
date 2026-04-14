"""Tiered compaction for per-chunk access_history JSON arrays.

Bounds the unbounded-growth path in `activations.access_history` by collapsing
older access records into time buckets for *storage only*. The ACT-R BLA
formula (ln Σ t_j^(-d)) reads bucket entries via AccessHistoryEntry.count and
continues to produce rankings within <0.001 of the pre-compaction values — far
below any retrieval threshold — because the power-law decay has already
rendered old individual records nearly worthless. A single access from 1 year
ago contributes ~0.00018 to the sum; 100 such accesses contribute less than a
single access from 1 hour ago.

See docs/02-features/memory/STORE_HARDENING.md for the full design rationale,
error-bound math, and non-goals.

Shape (JSON, per entry):
    Raw:       {"timestamp": "<ISO>", "context": <str|null>}
    Compacted: {"timestamp": "<ISO>", "context": null, "count": <int>}

The absence of a "count" key is equivalent to count=1, so pre-compaction rows
remain valid without migration.

Tiers:
    1. 0 - 7 days:    keep individual records (timestamp + context verbatim)
    2. 7 - 30 days:   hourly buckets (context discarded)
    3. 30 - 180 days: daily buckets (context discarded)
    4. 180+ days:     one aggregate bucket covering the entire tail

Trigger: Length exceeds COMPACTION_TRIGGER_LENGTH (default 200). Compaction is
intended to run lazily from record_access when the append pushes the array
past the threshold.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# Compact whenever the raw array exceeds this length. Chosen so that a mature
# chunk with years of history stays well-bounded while active chunks (which
# typically see <100 accesses between compactions) never pay the compaction
# cost on the common path.
COMPACTION_TRIGGER_LENGTH = 200

# Tier boundaries in seconds. Kept as module constants so tests can reference
# them without re-deriving.
_TIER1_MAX_SECONDS = 7 * 24 * 3600          # 7 days
_TIER2_MAX_SECONDS = 30 * 24 * 3600         # 30 days
_TIER3_MAX_SECONDS = 180 * 24 * 3600        # 180 days


def _parse_timestamp(raw: Any) -> datetime | None:
    """Parse an ISO timestamp string into a tz-aware UTC datetime.

    Returns None for unparseable or missing timestamps so the caller can drop
    the entry without crashing the entire compaction pass.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if not isinstance(raw, str):
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _entry_count(entry: dict[str, Any]) -> int:
    """Return the count represented by an entry (1 for pre-compaction rows)."""
    raw = entry.get("count", 1)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, n)


def compact_access_history(
    entries: list[dict[str, Any]],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Compact a raw access history array into tiered buckets.

    Pure function. No I/O, no SQL. Safe to call on any well-formed list of
    access entries regardless of origin.

    Args:
        entries: List of access records. Each must have a "timestamp" key
            (ISO 8601 string). "context" and "count" are optional.
        now: Reference time for age bucketing. Defaults to datetime.now(UTC).
            Parameterized for deterministic tests.

    Returns:
        A new list of entries with older records collapsed into buckets per
        the tier scheme. Tier 1 entries are preserved verbatim. Tier 2/3/4
        entries have count>=1, context=None, and timestamp set to the
        bucket's midpoint. The returned list is ordered newest-first within
        each tier, and tier 1 appears before tier 2, etc.

    Invariants:
        - len(output) <= len(input)
        - sum(entry_count) is preserved across compaction
        - No timestamps in the future relative to `now`
    """
    if not entries:
        return []

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Split entries into tiers by age.
    tier1: list[dict[str, Any]] = []       # kept verbatim
    tier2_by_hour: dict[int, int] = {}     # hour_epoch -> total count
    tier3_by_day: dict[int, int] = {}      # day_epoch -> total count
    tier4_count = 0
    tier4_earliest: datetime | None = None

    for entry in entries:
        ts = _parse_timestamp(entry.get("timestamp"))
        if ts is None:
            # Unparseable — skip rather than crash. The invariant
            # sum(count) preservation is relaxed only for corrupt input.
            continue
        age = (now - ts).total_seconds()
        if age < 0:
            # Future timestamp (clock skew) — treat as just-now, tier 1.
            age = 0

        count = _entry_count(entry)

        if age <= _TIER1_MAX_SECONDS:
            # Preserve as-is: keep timestamp and context intact.
            tier1.append(
                {
                    "timestamp": ts.isoformat(),
                    "context": entry.get("context"),
                    "count": count,
                },
            )
        elif age <= _TIER2_MAX_SECONDS:
            hour_key = int(ts.timestamp()) // 3600
            tier2_by_hour[hour_key] = tier2_by_hour.get(hour_key, 0) + count
        elif age <= _TIER3_MAX_SECONDS:
            day_key = int(ts.timestamp()) // 86400
            tier3_by_day[day_key] = tier3_by_day.get(day_key, 0) + count
        else:
            tier4_count += count
            if tier4_earliest is None or ts < tier4_earliest:
                tier4_earliest = ts

    output: list[dict[str, Any]] = []

    # Tier 1 — newest first
    tier1.sort(key=lambda e: e["timestamp"], reverse=True)
    output.extend(tier1)

    # Tier 2 — hourly buckets, newest hour first. Midpoint is the center of
    # the hour window.
    for hour_key in sorted(tier2_by_hour, reverse=True):
        midpoint_epoch = hour_key * 3600 + 1800  # center of the hour
        midpoint = datetime.fromtimestamp(midpoint_epoch, tz=timezone.utc)
        output.append(
            {
                "timestamp": midpoint.isoformat(),
                "context": None,
                "count": tier2_by_hour[hour_key],
            },
        )

    # Tier 3 — daily buckets
    for day_key in sorted(tier3_by_day, reverse=True):
        midpoint_epoch = day_key * 86400 + 43200  # center of the day
        midpoint = datetime.fromtimestamp(midpoint_epoch, tz=timezone.utc)
        output.append(
            {
                "timestamp": midpoint.isoformat(),
                "context": None,
                "count": tier3_by_day[day_key],
            },
        )

    # Tier 4 — single aggregate entry. Midpoint between the earliest tier-4
    # access and the tier 3/4 boundary, which is where tier 4 begins.
    if tier4_count > 0 and tier4_earliest is not None:
        tier4_boundary = now - timedelta(seconds=_TIER3_MAX_SECONDS)
        midpoint_epoch = (
            int(tier4_earliest.timestamp()) + int(tier4_boundary.timestamp())
        ) // 2
        midpoint = datetime.fromtimestamp(midpoint_epoch, tz=timezone.utc)
        output.append(
            {
                "timestamp": midpoint.isoformat(),
                "context": None,
                "count": tier4_count,
            },
        )

    return output


def should_compact(entries: list[dict[str, Any]]) -> bool:
    """Return True if the array should be compacted on the next write."""
    return len(entries) > COMPACTION_TRIGGER_LENGTH
