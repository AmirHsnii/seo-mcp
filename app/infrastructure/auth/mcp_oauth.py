"""MCP OAuth 2.1 endpoints for ChatGPT multi-tenant connectors.

Exposes authorization-server and protected-resource metadata, dynamic client
registration, authorize/token endpoints, and coordinates with Google OAuth so
each user stores their own Search Console refresh token.
"""

from __future__ import annotations

import secrets
import time
from urllib.parse import urlencode, urlparse, urlunparse

import httpx
from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.config import load_config
from app.infrastructure import token_store
from app.infrastructure.auth import oauth_store
from app.infrastructure.auth.mcp_jwt import sign_jwt, verify_pkce

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/webmasters.readonly",
]
_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"
_TOKEN_LIFETIME_SEC = 3600


def _base_url(cfg) -> str:
    return cfg.mcp_base_url.rstrip("/")


def _mcp_resource_url(cfg) -> str:
    return f"{_base_url(cfg)}/mcp"


def _build_google_flow(cfg) -> Flow:
    client_config = {
        "web": {
            "client_id": cfg.google_client_id,
            "client_secret": cfg.google_client_secret,
            "auth_uri": _AUTH_URI,
            "token_uri": _TOKEN_URI,
            "redirect_uris": [cfg.google_redirect_uri],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=cfg.google_redirect_uri,
        autogenerate_code_verifier=False,
    )


async def _google_sub_from_credentials(credentials, client_id: str) -> tuple[str, str | None]:
    """Return the Google account ``sub`` (and optional email) for token storage."""
    if credentials.id_token:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import id_token as google_id_token

        info = google_id_token.verify_oauth2_token(
            credentials.id_token,
            GoogleAuthRequest(),
            client_id,
        )
        sub = info.get("sub")
        if sub:
            return sub, info.get("email")

    if credentials.token:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                _USERINFO_URI,
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            if response.status_code == 200:
                data = response.json()
                sub = data.get("sub")
                if sub:
                    return sub, data.get("email")

    raise RuntimeError(
        "Could not determine Google account id — ensure openid scope is granted"
    )


async def authorization_server_metadata(_request: Request) -> JSONResponse:
    cfg = load_config()
    base = _base_url(cfg)
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }
    )


async def protected_resource_metadata(_request: Request) -> JSONResponse:
    cfg = load_config()
    base = _base_url(cfg)
    return JSONResponse(
        {
            "resource": _mcp_resource_url(cfg),
            "authorization_servers": [base],
            "bearer_methods_supported": ["header"],
        }
    )


async def register_client(request: Request) -> JSONResponse:
    body = await request.json()
    redirect_uris = body.get("redirect_uris")
    if not redirect_uris or not isinstance(redirect_uris, list):
        return JSONResponse(
            {"error": "invalid_client_metadata", "error_description": "redirect_uris required"},
            status_code=400,
        )
    return JSONResponse(oauth_store.register_client(redirect_uris), status_code=201)


async def authorize(request: Request) -> Response:
    cfg = load_config()
    params = request.query_params

    client_id = params.get("client_id")
    redirect_uri = params.get("redirect_uri")
    code_challenge = params.get("code_challenge")
    if not client_id or not redirect_uri or not code_challenge:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing OAuth parameters"},
            status_code=400,
        )

    if params.get("code_challenge_method", "S256") != "S256":
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Only S256 PKCE is supported"},
            status_code=400,
        )

    client = oauth_store.get_client(client_id)
    if client is None or redirect_uri not in client["redirect_uris"]:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Unknown client or redirect URI"},
            status_code=400,
        )

    resource = params.get("resource") or _mcp_resource_url(cfg)
    state_id = oauth_store.create_state(
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        resource=resource,
        external_state=params.get("state"),
    )

    flow = _build_google_flow(cfg)
    authorization_url, _google_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state_id,
    )
    return RedirectResponse(authorization_url)


async def token(request: Request) -> JSONResponse:
    cfg = load_config()
    form = await request.form()
    grant_type = form.get("grant_type")
    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    code = form.get("code")
    redirect_uri = form.get("redirect_uri")
    client_id = form.get("client_id")
    code_verifier = form.get("code_verifier")
    if not all([code, redirect_uri, client_id, code_verifier]):
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    stored = oauth_store.consume_code(str(code))
    if stored is None:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)

    if stored["client_id"] != client_id or stored["redirect_uri"] != redirect_uri:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)

    if not verify_pkce(str(code_verifier), stored["code_challenge"]):
        return JSONResponse({"error": "invalid_grant", "error_description": "PKCE failed"}, status_code=400)

    now = int(time.time())
    base = _base_url(cfg)
    jwt = sign_jwt(
        cfg.mcp_oauth_jwt_secret,
        {
            "iss": base,
            "sub": stored["google_sub"],
            "aud": stored["resource"] or _mcp_resource_url(cfg),
            "iat": now,
            "exp": now + _TOKEN_LIFETIME_SEC,
        },
    )
    return JSONResponse(
        {
            "access_token": jwt,
            "token_type": "Bearer",
            "expires_in": _TOKEN_LIFETIME_SEC,
        }
    )


async def google_callback(request: Request) -> Response:
    """Exchange Google's code, store per-user token, return MCP auth code."""
    cfg = load_config()
    error = request.query_params.get("error")
    if error:
        return JSONResponse({"error": error}, status_code=400)

    code = request.query_params.get("code")
    state_id = request.query_params.get("state")
    if not code or not state_id:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    oauth_state = oauth_store.consume_state(state_id)
    if oauth_state is None:
        return JSONResponse({"error": "invalid_state"}, status_code=400)

    flow = _build_google_flow(cfg)
    flow.fetch_token(code=code)
    credentials = flow.credentials
    if not credentials.refresh_token:
        return JSONResponse(
            {
                "error": "missing_refresh_token",
                "error_description": (
                    "Revoke this app at https://myaccount.google.com/permissions "
                    "and reconnect."
                ),
            },
            status_code=400,
        )

    import json

    try:
        google_sub, _email = await _google_sub_from_credentials(
            credentials, cfg.google_client_id
        )
    except Exception as exc:
        return JSONResponse(
            {
                "error": "account_identification_failed",
                "error_description": str(exc),
            },
            status_code=500,
        )

    token_store.save_token(json.loads(credentials.to_json()), google_sub=google_sub)

    if oauth_state["client_id"] == "legacy":
        from starlette.responses import PlainTextResponse

        return PlainTextResponse(
            f"Connected Google account {google_sub}. You can close this tab."
        )

    mcp_code = oauth_store.create_code(
        google_sub=google_sub,
        client_id=oauth_state["client_id"],
        redirect_uri=oauth_state["redirect_uri"],
        code_challenge=oauth_state["code_challenge"],
        resource=oauth_state["resource"],
    )

    parsed = urlparse(oauth_state["redirect_uri"])
    query_params = {"code": mcp_code}
    if oauth_state.get("external_state"):
        query_params["state"] = oauth_state["external_state"]
    query = urlencode(query_params)
    location = urlunparse(parsed._replace(query=query))
    return RedirectResponse(location)


async def legacy_google_start(_request: Request) -> RedirectResponse:
    """Manual one-off connect (admin/debug). Uses ephemeral state."""
    cfg = load_config()
    state_id = oauth_store.create_state(
        client_id="legacy",
        redirect_uri=cfg.google_redirect_uri,
        code_challenge=secrets.token_urlsafe(16),
        resource=None,
    )
    flow = _build_google_flow(cfg)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state_id,
    )
    return RedirectResponse(authorization_url)
