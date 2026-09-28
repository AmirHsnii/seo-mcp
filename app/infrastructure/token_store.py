"""Persistence of Google OAuth tokens to the durable data/ volume.

Multi-tenant: one token file per Google account (``data/tokens/{sub}.json``).
The legacy single-tenant file ``data/google_token.json`` is still read as a
fallback when no per-user token exists.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TOKEN_PATH = _DATA_DIR / "google_token.json"
_TOKENS_DIR = _DATA_DIR / "tokens"
_SUB_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _user_token_path(google_sub: str) -> Path:
    if not _SUB_PATTERN.match(google_sub):
        raise ValueError(f"Invalid google_sub: {google_sub!r}")
    return _TOKENS_DIR / f"{google_sub}.json"


def token_exists(google_sub: str | None = None) -> bool:
    if google_sub:
        return _user_token_path(google_sub).exists()
    if _TOKENS_DIR.exists() and any(_TOKENS_DIR.glob("*.json")):
        return True
    return TOKEN_PATH.exists()


def save_token(data: dict[str, Any], google_sub: str | None = None) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if google_sub:
        _TOKENS_DIR.mkdir(parents=True, exist_ok=True)
        path = _user_token_path(google_sub)
    else:
        path = TOKEN_PATH
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def load_token(google_sub: str | None = None) -> dict[str, Any]:
    if google_sub:
        path = _user_token_path(google_sub)
        if not path.exists():
            raise FileNotFoundError(f"No token for user {google_sub}")
        return json.loads(path.read_text(encoding="utf-8"))

    if _TOKENS_DIR.exists():
        tokens = sorted(_TOKENS_DIR.glob("*.json"))
        if len(tokens) == 1:
            return json.loads(tokens[0].read_text(encoding="utf-8"))

    if TOKEN_PATH.exists():
        return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))

    raise FileNotFoundError("No Google token stored")
