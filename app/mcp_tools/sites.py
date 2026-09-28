"""MCP tool: list_sites.

Thin FastMCP wrapper around ``app.services.gsc_service.list_sites``. Holds no
business logic — it only defines the tool contract (description + return
shape) and delegates to the services layer.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.services import gsc_service

# Every tool in this server is read-only: it never mutates GSC or the user's
# site, only reads data. Surfaced to hosts so they can allow it under
# read-only connector policies.
_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def list_sites() -> dict[str, list[dict[str, Any]]]:
    """List the Search Console properties this deployment can access.

    Returns every site (URL-prefix or ``sc-domain:`` property) that the
    connected Google account is verified as an owner or user of in Google
    Search Console. Call this first to discover the exact ``site_url`` values
    that the other tools (get_search_analytics, find_striking_distance_pages,
    inspect_url) expect — those tools need a property string that matches one
    returned here.

    Returns:
        ``{"sites": [{"site_url", "permission_level"}, ...]}`` where
        ``site_url`` is the property identifier and ``permission_level`` is the
        caller's GSC permission (e.g. "siteOwner", "siteFullUser").
    """
    return {"sites": gsc_service.list_sites()}


def register(mcp: FastMCP) -> None:
    """Register the list_sites tool on the shared FastMCP instance."""
    mcp.add_tool(list_sites, annotations=_READ_ONLY)
