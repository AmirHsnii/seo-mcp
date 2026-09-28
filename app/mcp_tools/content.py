"""MCP tool: fetch_page_content.

Thin FastMCP wrapper around
``app.services.content_service.fetch_page_content``. Declares the tool contract
and delegates crawling/extraction to the services layer.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from app.services import content_service

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def fetch_page_content(
    url: Annotated[
        str,
        Field(
            description=(
                "Absolute URL of the web page to read "
                '(e.g. "https://example.com/blog/post").'
            )
        ),
    ],
) -> dict[str, Any]:
    """Fetch a web page and extract its main readable content for SEO analysis.

    Crawls the page's raw HTML (with a fixed bot User-Agent), strips
    navigation/footer/scripts, and returns the primary article text plus the
    on-page SEO signals a model needs: title, meta description, and headings.
    Use this to evaluate what a page is about and what it might be missing to
    rank better. Note: JavaScript-heavy pages (SPAs without server-side
    rendering) may return incomplete text, since no JS is executed.

    Returns:
        On success: ``{"title", "meta_description", "headings", "main_text",
        "word_count"}`` where ``headings`` covers h1-h3. On a fetch failure
        (404/500/timeout/network error): ``{"url", "error", "status_code"}``
        with ``status_code`` null when there was no HTTP response.
    """
    return content_service.fetch_page_content(url)


def register(mcp: FastMCP) -> None:
    """Register the fetch_page_content tool on the shared FastMCP instance."""
    mcp.add_tool(fetch_page_content, annotations=_READ_ONLY)
