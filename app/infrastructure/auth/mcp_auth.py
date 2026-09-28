"""Bearer-token middleware guarding the MCP endpoint (auth Layer B).

The server is reachable on a public URL, so every request must present
``Authorization: Bearer <MCP_ACCESS_TOKEN>``. A missing or mismatched token gets
a 401 with ``{"error": "unauthorized"}``.

A few paths are excluded, because they must be reachable without the MCP token:
    * ``/health``          — container/monitoring healthcheck.
    * ``/robots.txt``      — must be served to public crawlers unauthenticated.
    * ``/oauth/google/*``  — the one-time Google connect flow (auth Layer A),
                             which the admin opens in a browser.

Implemented as raw ASGI middleware rather than Starlette's BaseHTTPMiddleware:
the MCP Streamable HTTP transport uses long-lived streaming responses, and
BaseHTTPMiddleware buffers the response body, which would break streaming.
"""

from __future__ import annotations

import hmac

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import load_config

_BEARER_PREFIX = "bearer "
_EXCLUDED_EXACT = frozenset({"/health", "/robots.txt"})
_EXCLUDED_PREFIXES = ("/oauth/google/",)


def _is_excluded(path: str) -> bool:
    """Return True for paths that must bypass the token check."""
    if path in _EXCLUDED_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Pull the raw token out of an ``Authorization: Bearer <token>`` header."""
    if not authorization:
        return None
    if authorization[: len(_BEARER_PREFIX)].lower() != _BEARER_PREFIX:
        return None
    return authorization[len(_BEARER_PREFIX):].strip()


class McpAuthMiddleware:
    """ASGI middleware enforcing the static MCP bearer token."""

    def __init__(self, app: ASGIApp, expected_token: str | None = None) -> None:
        self.app = app
        # Resolve the expected token once at startup. Allowing an override keeps
        # the middleware testable without touching the environment.
        self._expected_token = (
            expected_token
            if expected_token is not None
            else load_config().mcp_access_token
        )

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if _is_excluded(scope["path"]):
            await self.app(scope, receive, send)
            return

        token = _extract_bearer_token(Headers(scope=scope).get("authorization"))
        if token is None or not hmac.compare_digest(token, self._expected_token):
            response = JSONResponse({"error": "unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
