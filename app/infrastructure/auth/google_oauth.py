"""Google OAuth 2.0 Web-application flow (auth Layer A).

Exposes two Starlette routes:

    GET /oauth/google/start     -> redirect to Google's consent screen
    GET /oauth/google/callback  -> exchange the code and store the refresh token

Single-tenant: the admin (deployment owner) runs this once. The resulting
refresh token is persisted to data/google_token.json via token_store. This is
infrastructure — it performs network and disk I/O and knows about Google's SDK.
"""

from __future__ import annotations

import json

from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

from app.config import load_config
from app.infrastructure import token_store

# Read-only Search Console access is all we need (spec section 3, Layer A).
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_flow() -> Flow:
    """Construct the OAuth flow from the deployment's configured credentials."""
    cfg = load_config()
    client_config = {
        "web": {
            "client_id": cfg.google_client_id,
            "client_secret": cfg.google_client_secret,
            "auth_uri": _AUTH_URI,
            "token_uri": _TOKEN_URI,
            "redirect_uris": [cfg.google_redirect_uri],
        }
    }
    # Disable PKCE: recent google-auth-oauthlib enables it by default, which
    # sends a code_challenge at /start and expects the matching code_verifier at
    # /callback. This single-tenant flow builds a fresh Flow per request with no
    # session store, so the verifier from /start is lost and the token exchange
    # fails with "invalid_grant: Missing code verifier". Turning PKCE off keeps
    # the stateless two-request flow working.
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=cfg.google_redirect_uri,
        autogenerate_code_verifier=False,
    )


async def start(request: Request) -> RedirectResponse:
    """Redirect the admin to Google's consent screen.

    access_type=offline + prompt=consent guarantees Google returns a refresh
    token (rather than only an access token), which is what we persist.
    """
    flow = _build_flow()
    authorization_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Single-tenant admin flow: no session store, so state is not persisted or
    # verified here. Acceptable for a one-time self-host connect step.
    return RedirectResponse(authorization_url)


async def callback(request: Request) -> PlainTextResponse:
    """Handle Google's redirect: exchange the code and store the refresh token."""
    error = request.query_params.get("error")
    if error:
        return PlainTextResponse(
            f"Google returned an error: {error}. "
            "Try again at /oauth/google/start.",
            status_code=400,
        )

    code = request.query_params.get("code")
    if not code:
        return PlainTextResponse(
            "Missing authorization code. Start over at /oauth/google/start.",
            status_code=400,
        )

    flow = _build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    if not credentials.refresh_token:
        # Google only returns a refresh token when it hasn't already granted one
        # for this client. Revoke prior access, then retry.
        return PlainTextResponse(
            "Google did not return a refresh token. Remove this app's access at "
            "https://myaccount.google.com/permissions and reconnect via "
            "/oauth/google/start.",
            status_code=400,
        )

    token_store.save_token(json.loads(credentials.to_json()))
    return PlainTextResponse(
        "Connected to Google Search Console. You can close this tab."
    )


routes = [
    Route("/oauth/google/start", start, methods=["GET"]),
    Route("/oauth/google/callback", callback, methods=["GET"]),
]
