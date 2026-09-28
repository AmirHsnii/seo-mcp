"""ASGI middleware: validate MCP OAuth JWT and attach Google user context."""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import load_config
from app.infrastructure.auth.mcp_jwt import verify_jwt
from app.infrastructure.user_context import set_google_sub

_BEARER_PREFIX = "bearer "
_EXCLUDED_EXACT = frozenset({"/health", "/robots.txt"})
_EXCLUDED_PREFIXES = (
    "/oauth/",
    "/.well-known/",
)


def _is_excluded(path: str) -> bool:
    if path in _EXCLUDED_EXACT:
        return True
    if path == "/":
        return True
    return any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization[: len(_BEARER_PREFIX)].lower() != _BEARER_PREFIX:
        return None
    return authorization[len(_BEARER_PREFIX):].strip()


class McpOAuthMiddleware:
    """Require a valid MCP OAuth JWT on /mcp requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        cfg = load_config()
        self._secret = cfg.mcp_oauth_jwt_secret
        self._resource = f"{cfg.mcp_base_url.rstrip('/')}/mcp"
        self._metadata_url = (
            f"{cfg.mcp_base_url.rstrip('/')}/.well-known/oauth-protected-resource/mcp"
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        if _is_excluded(path):
            await self.app(scope, receive, send)
            return

        token = _extract_bearer(Headers(scope=scope).get("authorization"))
        if token is None:
            await self._unauthorized(scope, receive, send)
            return

        claims = verify_jwt(self._secret, token)
        if claims is None:
            await self._unauthorized(scope, receive, send)
            return

        aud = claims.get("aud")
        if aud not in (self._resource, self._resource + "/"):
            await self._unauthorized(scope, receive, send)
            return

        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub:
            await self._unauthorized(scope, receive, send)
            return

        set_google_sub(sub)
        await self.app(scope, receive, send)

    async def _unauthorized(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        response = Response(
            content='{"error":"unauthorized"}',
            status_code=401,
            media_type="application/json",
            headers={
                "WWW-Authenticate": (
                    f'Bearer realm="mcp", resource_metadata="{self._metadata_url}"'
                )
            },
        )
        await response(scope, receive, send)
