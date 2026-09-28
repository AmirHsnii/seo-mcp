"""Unit tests for app/domain/striking_distance.py (pure, no I/O)."""

from __future__ import annotations

from app.domain.striking_distance import filter_striking_distance


def _row(page: str, position: float, impressions: float) -> dict:
    return {
        "page": page,
        "position": position,
        "impressions": impressions,
        "clicks": 0,
        "ctr": 0.0,
    }


def test_position_range_boundaries_are_inclusive():
    rows = [
        _row("just-below", 4.99, 100),
        _row("at-min", 5.0, 100),
        _row("in-range", 10.0, 100),
        _row("at-max", 15.0, 100),
        _row("just-above", 15.01, 100),
    ]

    result = filter_striking_distance(rows)

    pages = {row["page"] for row in result}
    assert pages == {"at-min", "in-range", "at-max"}


def test_min_impressions_threshold_is_inclusive():
    rows = [
        _row("below", 8.0, 49),
        _row("at-threshold", 8.0, 50),
        _row("above", 8.0, 51),
    ]

    result = filter_striking_distance(rows)

    pages = {row["page"] for row in result}
    assert pages == {"at-threshold", "above"}


def test_sorted_by_impressions_descending():
    rows = [
        _row("low", 7.0, 60),
        _row("high", 12.0, 500),
        _row("mid", 9.0, 120),
    ]

    result = filter_striking_distance(rows)

    assert [row["page"] for row in result] == ["high", "mid", "low"]
    impressions = [row["impressions"] for row in result]
    assert impressions == sorted(impressions, reverse=True)


def test_custom_bounds_override_defaults():
    rows = [
        _row("a", 2.0, 100),
        _row("b", 3.0, 100),
        _row("c", 20.0, 100),
    ]

    result = filter_striking_distance(
        rows,
        position_min=1,
        position_max=3,
        min_impressions=10,
    )

    assert {row["page"] for row in result} == {"a", "b"}


def test_rows_missing_position_or_impressions_are_skipped():
    rows = [
        {"page": "no-position", "impressions": 100},
        {"page": "no-impressions", "position": 8.0},
        _row("valid", 8.0, 100),
    ]

    result = filter_striking_distance(rows)

    assert [row["page"] for row in result] == ["valid"]


def test_input_is_not_mutated():
    rows = [
        _row("b", 7.0, 60),
        _row("a", 12.0, 500),
    ]
    original_order = [row["page"] for row in rows]

    filter_striking_distance(rows)

    assert [row["page"] for row in rows] == original_order


def test_empty_input_returns_empty_list():
    assert filter_striking_distance([]) == []
