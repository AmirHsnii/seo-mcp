"""Striking-distance filtering — pure, side-effect-free.

"Striking distance" pages are those ranking just outside the top positions
(by default position 5-15) with enough impressions to be worth improving. This
module only reshapes an in-memory list of Search Analytics rows; it performs no
network calls, no Google API access, and no I/O.
"""

from __future__ import annotations

from typing import Any


def filter_striking_distance(
    rows: list[dict[str, Any]],
    position_min: float = 5,
    position_max: float = 15,
    min_impressions: float = 50,
) -> list[dict[str, Any]]:
    """Filter and rank striking-distance rows.

    Args:
        rows: Search Analytics rows (as produced by get_search_analytics). Each
            row is a dict expected to carry at least "position" and
            "impressions" (typically alongside "clicks", "ctr", and a dimension
            key such as "page"). Rows missing either "position" or
            "impressions" are skipped rather than raising.
        position_min: Inclusive lower bound on average position.
        position_max: Inclusive upper bound on average position.
        min_impressions: Inclusive minimum impressions threshold.

    Returns:
        A new list containing only the rows whose position falls within
        [position_min, position_max] and whose impressions are >=
        min_impressions, sorted by impressions descending. The input list and
        its dicts are never mutated.
    """
    matching: list[dict[str, Any]] = []
    for row in rows:
        position = row.get("position")
        impressions = row.get("impressions")
        if position is None or impressions is None:
            continue
        if position_min <= position <= position_max and impressions >= min_impressions:
            matching.append(row)

    return sorted(matching, key=lambda row: row["impressions"], reverse=True)
