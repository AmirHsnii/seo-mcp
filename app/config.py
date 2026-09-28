"""Application configuration.

Loads environment variables from a local .env file (if present) and validates
that every required variable is set. If any required variable is missing, a
clear ConfigError is raised listing exactly what to fix — rather than letting
the app crash later with an opaque error.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from dotenv import load_dotenv

# Load a local .env file if one exists. Real environment variables always take
# precedence (override=False), which is what we want in container deployments.
load_dotenv(override=False)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


# Environment variables that must always be present for the server to start.
# MCP_ACCESS_TOKEN is intentionally not here: it is only required when the
# bearer-token guard (auth Layer B) is enabled — see _read_auth_enabled.
_REQUIRED_VARS = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
)

_DEFAULT_PORT = 8000

# Accepted truthy/falsey spellings for MCP_AUTH_ENABLED.
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_VALID_AUTH_MODES = frozenset({"oauth", "bearer", "none"})


@dataclass(frozen=True)
class Config:
    """Validated application configuration."""

    mcp_auth_enabled: bool
    # None when auth Layer B is disabled (MCP_AUTH_ENABLED=false); otherwise the
    # required static bearer token.
    mcp_access_token: str | None
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    public_host: str
    mcp_public_hosts: tuple[str, ...]
    mcp_base_url: str
    mcp_oauth_jwt_secret: str
    mcp_auth_mode: str
    port: int


def _read_auth_enabled() -> bool:
    """Parse the optional MCP_AUTH_ENABLED flag, defaulting to True.

    When enabled, the MCP endpoint is guarded by the static bearer token
    (auth Layer B). It must be disabled for ChatGPT's developer-mode connectors,
    which can only send OAuth or no auth — not a static bearer header.
    """
    raw = os.environ.get("MCP_AUTH_ENABLED")
    if raw is None or raw.strip() == "":
        return True
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ConfigError(
        f"MCP_AUTH_ENABLED must be a boolean (true/false), got {raw!r}. "
        "Fix it in your environment or .env file."
    )


def _read_port() -> int:
    """Parse the optional PORT variable, defaulting to 8000."""
    raw = os.environ.get("PORT")
    if raw is None or raw.strip() == "":
        return _DEFAULT_PORT
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"PORT must be an integer, got {raw!r}. "
            "Fix the PORT value in your environment or .env file."
        ) from exc


def _read_auth_mode(auth_enabled: bool) -> str:
    raw = os.environ.get("MCP_AUTH_MODE", "").strip().lower()
    if raw:
        if raw not in _VALID_AUTH_MODES:
            raise ConfigError(
                f"MCP_AUTH_MODE must be one of oauth/bearer/none, got {raw!r}."
            )
        return raw
    if auth_enabled:
        return "bearer"
    return "oauth"


def load_config() -> Config:
    """Load and validate configuration.

    Raises:
        ConfigError: if one or more required environment variables are missing,
            with a message naming every missing variable and pointing to
            .env.example.
    """
    auth_enabled = _read_auth_enabled()
    auth_mode = _read_auth_mode(auth_enabled)

    required = list(_REQUIRED_VARS)
    if auth_mode == "bearer":
        required.append("MCP_ACCESS_TOKEN")
    if auth_mode == "oauth":
        if not os.environ.get("MCP_OAUTH_JWT_SECRET", "").strip():
            required.append("MCP_OAUTH_JWT_SECRET")
        # MCP_BASE_URL is optional — derived from GOOGLE_REDIRECT_URI when absent.

    missing = [
        name
        for name in required
        if not (os.environ.get(name) or "").strip()
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Set them in your environment or copy .env.example to .env and "
            "fill in the values."
        )

    token = os.environ.get("MCP_ACCESS_TOKEN", "").strip()
    redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    public_host = urlsplit(redirect_uri).netloc
    if not public_host:
        raise ConfigError(
            f"GOOGLE_REDIRECT_URI must be an absolute URL, got {redirect_uri!r}. "
            "Example: https://mcp.example.com/oauth/google/callback"
        )

    mcp_base_url = os.environ.get("MCP_BASE_URL", "").strip()
    if not mcp_base_url:
        # Derive from redirect URI when not explicitly set.
        parts = urlsplit(redirect_uri)
        mcp_base_url = f"{parts.scheme}://{parts.netloc}"

    extra_hosts = tuple(
        h.strip()
        for h in os.environ.get("MCP_PUBLIC_HOSTS", "").split(",")
        if h.strip()
    )
    mcp_public_hosts = extra_hosts
    base_host = urlsplit(mcp_base_url).netloc
    if base_host and base_host not in mcp_public_hosts:
        mcp_public_hosts = (base_host, *mcp_public_hosts)

    return Config(
        mcp_auth_enabled=auth_enabled,
        mcp_access_token=token if auth_mode == "bearer" else None,
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        google_redirect_uri=redirect_uri,
        public_host=public_host,
        mcp_public_hosts=mcp_public_hosts,
        mcp_base_url=mcp_base_url,
        mcp_oauth_jwt_secret=os.environ.get("MCP_OAUTH_JWT_SECRET", "").strip(),
        mcp_auth_mode=auth_mode,
        port=_read_port(),
    )
