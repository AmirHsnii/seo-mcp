"""Google Search Console API client factory (auth Layer A, read side)."""

from __future__ import annotations

import json

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from app.infrastructure import token_store
from app.infrastructure.user_context import get_google_sub

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

_NOT_CONNECTED_MESSAGE = (
    "Not connected to Google yet — complete OAuth in ChatGPT connector settings"
)
_RECONNECT_MESSAGE = (
    "Google access has been revoked or expired — reconnect the ChatGPT connector"
)


class GoogleNotConnectedError(RuntimeError):
    """Raised when no Google token has been stored yet."""


class GoogleReconnectRequiredError(RuntimeError):
    """Raised when the stored refresh token is no longer valid (invalid_grant)."""


def get_gsc_service() -> Resource:
    """Return an authenticated Search Console v1 service for the current user."""
    google_sub = get_google_sub()
    if not token_store.token_exists(google_sub):
        raise GoogleNotConnectedError(_NOT_CONNECTED_MESSAGE)

    credentials = Credentials.from_authorized_user_info(
        token_store.load_token(google_sub), scopes=SCOPES
    )

    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError as exc:
                if "invalid_grant" in str(exc).lower():
                    raise GoogleReconnectRequiredError(_RECONNECT_MESSAGE) from exc
                raise
            token_store.save_token(
                json.loads(credentials.to_json()), google_sub=google_sub
            )
        else:
            raise GoogleReconnectRequiredError(_RECONNECT_MESSAGE)

    return build(
        "searchconsole",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )
