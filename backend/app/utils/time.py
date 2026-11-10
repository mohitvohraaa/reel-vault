"""Timestamp parsing helpers for Instagram exports."""
from __future__ import annotations

from datetime import datetime, timezone


def ms_to_datetime(value) -> datetime | None:
    """Convert an Instagram ``timestamp_ms`` to a timezone-aware UTC datetime.

    Robust to values given in seconds, milliseconds, strings, floats, or None.
    """
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num <= 0:
        return None
    # Heuristic: >1e12 → milliseconds; otherwise seconds.
    seconds = num / 1000.0 if num > 1_000_000_000_000 else num
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
