"""Shared httpx wrapper with sensible defaults.

Both sitemap fetching and page-content crawling need the same behaviour: a
bounded timeout, a stable User-Agent so remote servers can identify the bot,
and a single point that turns a non-2xx response into a clear exception. Keeping
that here means callers do a plain ``fetch(url)`` instead of repeating timeout,
header, and status-check boilerplate.
"""

from __future__ import annotations

import httpx

# Sensible defaults shared by every outbound request (spec section 3, Layer B).
DEFAULT_TIMEOUT = 10.0
USER_AGENT = "SEO-MCP-Bot/1.0"


class HttpFetchError(RuntimeError):
    """Raised when a request fails or returns a non-2xx status.

    Carries the offending URL and status code (when there was a response) so
    callers can surface a clear message without inspecting httpx internals.
    """

    def __init__(
        self,
        message: str,
        *,
        url: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code


def fetch(url: str, timeout: float | None = None) -> httpx.Response:
    """Fetch ``url`` and return the response, raising on any failure.

    Applies the shared User-Agent and a 10-second default timeout, and follows
    redirects (common for sitemaps and canonical page URLs).

    Args:
        url: The absolute URL to GET.
        timeout: Optional override for the request timeout, in seconds. Defaults
            to ``DEFAULT_TIMEOUT`` when not given.

    Returns:
        The successful ``httpx.Response`` (status in the 2xx range).

    Raises:
        HttpFetchError: if the request could not be completed (network error,
            timeout, ...) or the server returned a non-2xx status.
    """
    effective_timeout = DEFAULT_TIMEOUT if timeout is None else timeout
    headers = {"User-Agent": USER_AGENT}

    try:
        response = httpx.get(
            url,
            timeout=effective_timeout,
            headers=headers,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        raise HttpFetchError(
            f"Request to {url} failed: {exc}", url=url
        ) from exc

    if not response.is_success:
        raise HttpFetchError(
            f"GET {url} returned HTTP {response.status_code}",
            url=url,
            status_code=response.status_code,
        )

    return response
