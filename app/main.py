"""Entrypoint: build the FastMCP instance and mount it on Starlette."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

from app.config import load_config
from app.infrastructure.auth import mcp_oauth
from app.infrastructure.auth.mcp_auth import McpAuthMiddleware
from app.web.mcp_oauth_middleware import McpOAuthMiddleware
from app.web.noindex import NoIndexMiddleware

_ROBOTS_TXT = Path(__file__).resolve().parent.parent / "robots.txt"


def _build_transport_security(cfg) -> TransportSecuritySettings:
    base_host = urlsplit(cfg.mcp_base_url).netloc
    hosts: list[str] = [
        base_host,
        f"{base_host}:*",
        cfg.public_host,
        f"{cfg.public_host}:*",
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
    ]
    origins = [
        f"https://{base_host}",
        f"https://{base_host}:*",
        f"https://{cfg.public_host}",
        f"https://{cfg.public_host}:*",
    ]
    for host in cfg.mcp_public_hosts:
        if host:
            hosts.extend((host, f"{host}:*"))
            origins.extend((f"https://{host}", f"https://{host}:*"))

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def _register_tools(mcp: FastMCP) -> None:
    from app import mcp_tools

    register = getattr(mcp_tools, "register_tools", None)
    if register is not None:
        register(mcp)


def create_app() -> Starlette:
    cfg = load_config()

    mcp = FastMCP("seo-mcp", transport_security=_build_transport_security(cfg))
    _register_tools(mcp)

    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def root(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "service": "seo-mcp",
                "status": "ok",
                "mcp": "/mcp",
                "health": "/health",
                "auth_mode": cfg.mcp_auth_mode,
            }
        )

    async def robots(_request: Request) -> FileResponse:
        return FileResponse(_ROBOTS_TXT, media_type="text/plain")

    mcp.custom_route("/", methods=["GET"])(root)
    mcp.custom_route("/health", methods=["GET"])(health)
    mcp.custom_route("/robots.txt", methods=["GET"])(robots)

    mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(
        mcp_oauth.authorization_server_metadata
    )
    mcp.custom_route(
        "/.well-known/oauth-protected-resource/mcp", methods=["GET"]
    )(mcp_oauth.protected_resource_metadata)
    mcp.custom_route("/oauth/register", methods=["POST"])(mcp_oauth.register_client)
    mcp.custom_route("/oauth/authorize", methods=["GET"])(mcp_oauth.authorize)
    mcp.custom_route("/oauth/token", methods=["POST"])(mcp_oauth.token)
    mcp.custom_route("/oauth/google/callback", methods=["GET"])(
        mcp_oauth.google_callback
    )
    mcp.custom_route("/oauth/google/start", methods=["GET"])(
        mcp_oauth.legacy_google_start
    )

    app = mcp.streamable_http_app()

    if cfg.mcp_auth_mode == "bearer":
        app.add_middleware(McpAuthMiddleware)
    elif cfg.mcp_auth_mode == "oauth":
        app.add_middleware(McpOAuthMiddleware)

    app.add_middleware(NoIndexMiddleware)
    return app


app = create_app()
