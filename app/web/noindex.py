"""Middleware adding ``X-Robots-Tag: noindex, nofollow`` to every response.

The server sits on a public URL (Tailscale Funnel / subdomain), so search
engines could otherwise crawl and index it. This header tells them not to
index any page or follow any link, on every response — a belt-and-braces
complement to ``robots.txt`` (spec sections 6 and 7).

Implemented as raw ASGI middleware, not Starlette's BaseHTTPMiddleware,
because the MCP Streamable HTTP transport uses long-lived streaming responses
that BaseHTTPMiddleware would buffer and break. Here we only rewrite the
``http.response.start`` headers and leave the body stream untouched.
"""

from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_HEADER_NAME = "x-robots-tag"
_HEADER_VALUE = "noindex, nofollow"


class NoIndexMiddleware:
    """ASGI middleware stamping X-Robots-Tag on every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[_HEADER_NAME] = _HEADER_VALUE
            await send(message)

        await self.app(scope, receive, send_with_header)
