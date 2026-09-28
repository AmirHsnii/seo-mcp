"""MCP tool: fetch_sitemap.

Thin FastMCP wrapper around ``app.services.sitemap_service.fetch_sitemap``.
Declares the tool contract and delegates fetching/parsing to the services
layer.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from app.services import sitemap_service

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def fetch_sitemap(
    sitemap_url: Annotated[
        str,
        Field(
            description=(
                "Absolute URL of an XML sitemap or sitemap index "
                '(e.g. "https://example.com/sitemap.xml").'
            )
        ),
    ],
) -> dict[str, Any]:
    """Fetch a sitemap and list every page URL it contains.

    Downloads and parses an XML sitemap. If the URL is a sitemap index
    (``<sitemapindex>``), nested sitemaps are followed recursively and their
    URLs merged into a single flat list. Use this to enumerate a site's pages —
    for example to pick which URLs to inspect or crawl with the other tools.

    Returns:
        ``{"pages": [...], "count": <int>}``. Each entry is either
        ``{"url", "lastmod"}`` (``lastmod`` may be null) for a page, or
        ``{"url", "error"}`` when a nested sitemap could not be fetched or
        parsed. ``count`` is the number of entries returned.
    """
    pages = sitemap_service.fetch_sitemap(sitemap_url)
    return {"pages": pages, "count": len(pages)}


def register(mcp: FastMCP) -> None:
    """Register the fetch_sitemap tool on the shared FastMCP instance."""
    mcp.add_tool(fetch_sitemap, annotations=_READ_ONLY)
