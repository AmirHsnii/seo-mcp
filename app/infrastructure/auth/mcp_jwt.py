"""Sign and verify short-lived MCP access tokens (JWT, HS256)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return hmac.compare_digest(computed, code_challenge)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_jwt(secret: str, claims: dict[str, Any]) -> str:
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload = _b64url_encode(
        json.dumps(claims, separators=(",", ":")).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    signature = _b64url_encode(
        hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{signature}"


def verify_jwt(secret: str, token: str) -> dict[str, Any] | None:
    try:
        header_b64, payload_b64, signature = token.split(".", 2)
    except ValueError:
        return None

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = _b64url_encode(
        hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected, signature):
        return None

    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError):
        return None

    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or exp < time.time():
        return None
    return claims
