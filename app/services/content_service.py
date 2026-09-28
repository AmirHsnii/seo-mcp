"""Business logic for page content extraction (backs the fetch_page_content tool).

Orchestrates the shared HTTP client (app.infrastructure.http_client) and the
pure content extractor (app.domain.content_extractor). Fetching happens here;
parsing stays pure in the domain layer. A fetch failure is turned into a plain
error dict so the MCP tool layer can hand it back to the model instead of
crashing.
"""

from __future__ import annotations

from typing import Any

from app.domain.content_extractor import extract_content
from app.infrastructure import http_client

# Page crawls can be slower than sitemap fetches; give them extra headroom.
_FETCH_TIMEOUT = 15.0


def fetch_page_content(url: str) -> dict[str, Any]:
    """Fetch a page and return its extracted content, or an error dict.

    Args:
        url: The absolute URL of the page to crawl.

    Returns:
        On success, the structured result from extract_content (title,
        meta_description, headings, main_text, word_count). On a fetch failure
        (404/500/timeout/network error), a dict shaped as
        {"url", "error", "status_code"} where status_code is None when there
        was no HTTP response.
    """
    try:
        response = http_client.fetch(url, timeout=_FETCH_TIMEOUT)
    except http_client.HttpFetchError as exc:
        return {
            "url": url,
            "error": str(exc),
            "status_code": exc.status_code,
        }

    return extract_content(response.text, url)
