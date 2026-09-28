"""Business logic for sitemap extraction (backs the fetch_sitemap tool).

Orchestrates the shared HTTP client (app.infrastructure.http_client) and the
pure sitemap parser (app.domain.sitemap_parser). Fetching lives here; parsing
stays pure in the domain layer. Nested <sitemapindex> documents are followed
recursively (bounded to prevent loops), and a failure in one nested sitemap is
recorded rather than aborting the whole crawl.
"""

from __future__ import annotations

from typing import Any

from app.domain.sitemap_parser import parse_sitemap
from app.infrastructure import http_client

# A sitemap index may point at further indexes; cap recursion so a
# self-referential or cyclic set of sitemaps can't loop forever.
_MAX_DEPTH = 2


def fetch_sitemap(sitemap_url: str, _depth: int = 0) -> list[dict[str, Any]]:
    """Fetch a sitemap and return a flat list of discovered pages.

    Args:
        sitemap_url: URL of the sitemap or sitemap index to fetch.
        _depth: Internal recursion depth guard; callers should not set it.

    Returns:
        A flat list of {"url", "lastmod"} entries for every page URL found,
        recursing into nested sitemaps. If a nested sitemap cannot be fetched
        or parsed, its entry is included as {"url", "error"} instead of
        aborting the whole call.
    """
    response = http_client.fetch(sitemap_url)
    entries = parse_sitemap(response.content)

    pages: list[dict[str, Any]] = []
    for entry in entries:
        loc = entry.get("loc")
        if entry.get("type") == "sitemap":
            if _depth >= _MAX_DEPTH:
                pages.append(
                    {
                        "url": loc,
                        "error": f"max sitemap nesting depth ({_MAX_DEPTH}) exceeded",
                    }
                )
                continue
            try:
                pages.extend(fetch_sitemap(loc, _depth=_depth + 1))
            except Exception as exc:  # noqa: BLE001 — isolate one bad nested sitemap
                pages.append({"url": loc, "error": str(exc)})
        else:
            pages.append({"url": loc, "lastmod": entry.get("lastmod")})

    return pages
