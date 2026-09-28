"""MCP tools: get_search_analytics, find_striking_distance_pages.

Thin FastMCP wrappers around ``app.services.gsc_service``. They declare the
tool contract (typed inputs, rich descriptions, JSON-serializable output) and
delegate all querying/filtering to the services layer.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from app.services import gsc_service

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def get_search_analytics(
    site_url: Annotated[
        str,
        Field(
            description=(
                "The GSC property to query, exactly as returned by list_sites "
                '(e.g. "https://example.com/" or "sc-domain:example.com").'
            )
        ),
    ],
    start_date: Annotated[
        str,
        Field(description="Inclusive start date in YYYY-MM-DD format."),
    ],
    end_date: Annotated[
        str,
        Field(description="Inclusive end date in YYYY-MM-DD format."),
    ],
    dimensions: Annotated[
        list[str],
        Field(
            description=(
                "Dimensions to group results by. Each must be one of: "
                '"query", "page", "date", "device", "country". Order matters — '
                "each row's keys are returned under these dimension names."
            )
        ),
    ],
    filters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            default=None,
            description=(
                "Optional Search Analytics dimension filters, combined with "
                "AND. Each filter is an object like "
                '{"dimension": "query", "operator": "contains", '
                '"expression": "shoes"}. Operators: equals, notEquals, '
                "contains, notContains, includingRegex, excludingRegex."
            ),
        ),
    ] = None,
    row_limit: Annotated[
        int,
        Field(
            default=100,
            ge=1,
            le=25000,
            description=(
                "Maximum number of rows to return (1-25000), sorted by clicks "
                "descending. Defaults to 100, which is plenty for 'top "
                "queries/pages' questions and keeps the response small. Only "
                "raise it when the user explicitly needs a large export; large "
                "values (e.g. query+page over a long range) can return tens of "
                "thousands of rows."
            ),
        ),
    ] = 100,
) -> dict[str, list[dict[str, Any]]]:
    """Query Google Search Console Search Analytics for a property.

    Returns per-row search performance metrics (clicks, impressions, CTR,
    average position) grouped by the requested dimensions over the date range.
    Use this for questions like "top queries last month", "which pages get the
    most impressions", or "traffic by country/device". This is the general
    Search Analytics endpoint; for the specific "pages worth optimizing" case,
    prefer find_striking_distance_pages, which pre-applies the right filters.

    Returns:
        ``{"rows": [...]}``. Each row contains the requested dimension values
        keyed by dimension name (e.g. ``"query"``, ``"page"``) plus the
        metrics ``clicks``, ``impressions``, ``ctr`` (0-1), and ``position``.
    """
    rows = gsc_service.get_search_analytics(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        filters=filters,
        row_limit=row_limit,
    )
    return {"rows": rows}


def find_striking_distance_pages(
    site_url: Annotated[
        str,
        Field(
            description=(
                "The GSC property to query, exactly as returned by list_sites "
                '(e.g. "https://example.com/" or "sc-domain:example.com").'
            )
        ),
    ],
    start_date: Annotated[
        str,
        Field(description="Inclusive start date in YYYY-MM-DD format."),
    ],
    end_date: Annotated[
        str,
        Field(description="Inclusive end date in YYYY-MM-DD format."),
    ],
    position_min: Annotated[
        float,
        Field(
            default=5.0,
            description="Lowest (best) average position to include, inclusive.",
        ),
    ] = 5.0,
    position_max: Annotated[
        float,
        Field(
            default=15.0,
            description="Highest (worst) average position to include, inclusive.",
        ),
    ] = 15.0,
    min_impressions: Annotated[
        float,
        Field(
            default=50.0,
            description="Minimum impressions a page needs to be included.",
        ),
    ] = 50.0,
) -> dict[str, list[dict[str, Any]]]:
    """Find "striking distance" pages: high-impression pages ranking just off page 1.

    Convenience wrapper over Search Analytics (grouped by page) that returns
    pages whose average position falls between ``position_min`` and
    ``position_max`` (default 5-15) and that already earn at least
    ``min_impressions`` impressions (default 50), sorted by impressions
    descending. These are the best SEO improvement opportunities — pages close
    to page 1 with proven demand — so a small ranking gain can yield outsized
    click growth. Use this instead of get_search_analytics when the user asks
    which pages to improve/optimize.

    Returns:
        ``{"pages": [...]}`` where each entry has ``page``, ``clicks``,
        ``impressions``, ``ctr`` (0-1), and ``position``, ordered by
        impressions descending.
    """
    pages = gsc_service.find_striking_distance_pages(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        position_min=position_min,
        position_max=position_max,
        min_impressions=min_impressions,
    )
    return {"pages": pages}


def register(mcp: FastMCP) -> None:
    """Register both search-analytics tools on the shared FastMCP instance."""
    mcp.add_tool(get_search_analytics, annotations=_READ_ONLY)
    mcp.add_tool(find_striking_distance_pages, annotations=_READ_ONLY)
