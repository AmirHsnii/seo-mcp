"""Business logic for Google Search Console data (auth Layer A, read side).

Orchestrates the authenticated Search Console service from
``app.infrastructure.google_api_client`` and the pure domain filtering in
``app.domain.striking_distance``. Backs the list_sites, get_search_analytics,
find_striking_distance_pages, and inspect_url tools.

This layer talks to Google and reshapes responses into simple, MCP-friendly
structures; it never reimplements domain logic (e.g. striking-distance
filtering is delegated to the domain module).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.striking_distance import filter_striking_distance
from app.infrastructure.google_api_client import get_gsc_service

_DATE_FORMAT = "%Y-%m-%d"


def _validate_date(value: str, field_name: str) -> None:
    """Ensure a date string is in YYYY-MM-DD form, else raise ValueError."""
    try:
        datetime.strptime(value, _DATE_FORMAT)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"{field_name} must be in YYYY-MM-DD format, got {value!r}"
        ) from exc


def _flatten_row(row: dict[str, Any], dimensions: list[str]) -> dict[str, Any]:
    """Map a raw Search Analytics row's dimension keys onto their names.

    A raw row looks like ``{"keys": ["/page"], "clicks": ..., "impressions":
    ..., "ctr": ..., "position": ...}``. This zips ``keys`` with the requested
    ``dimensions`` so callers (and the domain layer) can read ``row["page"]``
    directly while keeping the metric fields intact.
    """
    flattened: dict[str, Any] = dict(zip(dimensions, row.get("keys", [])))
    for metric in ("clicks", "impressions"):
        if metric in row:
            flattened[metric] = row[metric]
    # Round the ratio/position metrics: the API returns ~17 significant digits
    # (e.g. 0.015871619927623024), which bloats the payload and adds no useful
    # precision for downstream analysis.
    if "ctr" in row:
        flattened["ctr"] = round(row["ctr"], 4)
    if "position" in row:
        flattened["position"] = round(row["position"], 2)
    return flattened


def list_sites() -> list[dict[str, str]]:
    """Return verified GSC sites as a list of {site_url, permission_level}."""
    service = get_gsc_service()
    response = service.sites().list().execute()
    return [
        {
            "site_url": entry.get("siteUrl"),
            "permission_level": entry.get("permissionLevel"),
        }
        for entry in response.get("siteEntry", [])
    ]


def get_search_analytics(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    filters: list[dict[str, Any]] | None = None,
    row_limit: int = 1000,
) -> list[dict[str, Any]]:
    """Query the Search Analytics API and return flattened metric rows.

    Args:
        site_url: The GSC property (e.g. "https://example.com/" or
            "sc-domain:example.com").
        start_date: Inclusive start date, YYYY-MM-DD.
        end_date: Inclusive end date, YYYY-MM-DD.
        dimensions: Dimensions to group by (query/page/date/device/country).
        filters: Optional list of Search Analytics dimension filters; wrapped
            into a single dimensionFilterGroup.
        row_limit: Maximum number of rows to return.

    Returns:
        Rows with the requested dimension values keyed by name plus
        clicks/impressions/ctr/position.
    """
    _validate_date(start_date, "start_date")
    _validate_date(end_date, "end_date")

    body: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]

    service = get_gsc_service()
    response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return [_flatten_row(row, dimensions) for row in response.get("rows", [])]


def find_striking_distance_pages(
    site_url: str,
    start_date: str,
    end_date: str,
    position_min: float = 5,
    position_max: float = 15,
    min_impressions: float = 50,
) -> list[dict[str, Any]]:
    """Find pages ranking in striking distance, sorted by impressions desc.

    Thin wrapper: pulls page-level Search Analytics rows and delegates all
    filtering/sorting to app.domain.striking_distance.filter_striking_distance.
    """
    # Request a generous page pool (the API sorts by clicks, but striking-
    # distance pages can have high impressions yet modest clicks). The domain
    # filter below trims this to only the matching pages, so the tool's output
    # stays small regardless of this limit.
    rows = get_search_analytics(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["page"],
        row_limit=5000,
    )
    return filter_striking_distance(
        rows,
        position_min=position_min,
        position_max=position_max,
        min_impressions=min_impressions,
    )


def inspect_url(site_url: str, inspection_url: str) -> dict[str, Any]:
    """Inspect a URL's index status and return a summarized result.

    Returns a compact dict with verdict, coverageState, and mobileUsability
    rather than the full URL Inspection API response.
    """
    service = get_gsc_service()
    response = (
        service.urlInspection()
        .index()
        .inspect(
            body={"inspectionUrl": inspection_url, "siteUrl": site_url}
        )
        .execute()
    )

    result = response.get("inspectionResult", {})
    index_status = result.get("indexStatusResult", {})
    mobile_usability = result.get("mobileUsabilityResult", {})

    return {
        "verdict": index_status.get("verdict"),
        "coverageState": index_status.get("coverageState"),
        "mobileUsability": mobile_usability.get("verdict"),
    }
