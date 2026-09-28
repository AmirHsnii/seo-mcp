"""MCP tool: inspect_url.

Thin FastMCP wrapper around ``app.services.gsc_service.inspect_url``. Declares
the tool contract and delegates the URL Inspection API call to the services
layer.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from app.services import gsc_service

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def inspect_url(
    site_url: Annotated[
        str,
        Field(
            description=(
                "The GSC property that owns the URL, exactly as returned by "
                'list_sites (e.g. "https://example.com/" or '
                '"sc-domain:example.com").'
            )
        ),
    ],
    inspection_url: Annotated[
        str,
        Field(
            description=(
                "The absolute URL to inspect. Must belong to the given "
                "property (e.g. \"https://example.com/blog/post\")."
            )
        ),
    ],
) -> dict[str, Any]:
    """Check whether a specific URL is indexed by Google (URL Inspection API).

    Reports Google's current index status for one page: whether it is indexed,
    its coverage state (e.g. "Submitted and indexed", "Crawled - currently not
    indexed"), and its mobile-usability verdict. Use this to diagnose why a
    page is or isn't ranking, or to confirm indexing after publishing changes.
    The ``inspection_url`` must be under the given ``site_url`` property.

    Returns:
        ``{"verdict", "coverageState", "mobileUsability"}`` — a compact summary
        of the URL Inspection result (any field may be null if Google did not
        report it).
    """
    return gsc_service.inspect_url(
        site_url=site_url,
        inspection_url=inspection_url,
    )


def register(mcp: FastMCP) -> None:
    """Register the inspect_url tool on the shared FastMCP instance."""
    mcp.add_tool(inspect_url, annotations=_READ_ONLY)
