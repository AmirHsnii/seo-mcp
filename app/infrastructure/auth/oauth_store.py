"""SQLite store for MCP OAuth clients, auth states, and authorization codes."""

from __future__ import annotations

import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "oauth.db"

_STATE_TTL_SEC = 300
_CODE_TTL_SEC = 120


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS oauth_clients (
            client_id TEXT PRIMARY KEY,
            redirect_uris TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oauth_states (
            state_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            redirect_uri TEXT NOT NULL,
            code_challenge TEXT NOT NULL,
            resource TEXT,
            external_state TEXT,
            created_at REAL NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS oauth_codes (
            code TEXT PRIMARY KEY,
            google_sub TEXT NOT NULL,
            client_id TEXT NOT NULL,
            redirect_uri TEXT NOT NULL,
            code_challenge TEXT NOT NULL,
            resource TEXT,
            created_at REAL NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    try:
        conn.execute("ALTER TABLE oauth_states ADD COLUMN external_state TEXT")
    except sqlite3.OperationalError:
        pass
    return conn


def register_client(redirect_uris: list[str]) -> dict[str, Any]:
    client_id = secrets.token_urlsafe(16)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO oauth_clients (client_id, redirect_uris, created_at) "
            "VALUES (?, ?, ?)",
            (client_id, json.dumps(redirect_uris), time.time()),
        )
    return {
        "client_id": client_id,
        "client_id_issued_at": int(time.time()),
        "redirect_uris": redirect_uris,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }


def get_client(client_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
    if row is None:
        return None
    return {
        "client_id": row["client_id"],
        "redirect_uris": json.loads(row["redirect_uris"]),
    }


def create_state(
    *,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    resource: str | None,
    external_state: str | None = None,
) -> str:
    state_id = secrets.token_urlsafe(24)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO oauth_states "
            "(state_id, client_id, redirect_uri, code_challenge, resource, "
            "external_state, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                state_id,
                client_id,
                redirect_uri,
                code_challenge,
                resource,
                external_state,
                time.time(),
            ),
        )
    return state_id


def consume_state(state_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_states WHERE state_id = ? AND used = 0",
            (state_id,),
        ).fetchone()
        if row is None:
            return None
        if time.time() - row["created_at"] > _STATE_TTL_SEC:
            return None
        conn.execute(
            "UPDATE oauth_states SET used = 1 WHERE state_id = ?", (state_id,)
        )
    return dict(row)


def create_code(
    *,
    google_sub: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    resource: str | None,
) -> str:
    code = secrets.token_urlsafe(32)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO oauth_codes "
            "(code, google_sub, client_id, redirect_uri, code_challenge, "
            "resource, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                code,
                google_sub,
                client_id,
                redirect_uri,
                code_challenge,
                resource,
                time.time(),
            ),
        )
    return code


def consume_code(code: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_codes WHERE code = ? AND used = 0", (code,)
        ).fetchone()
        if row is None:
            return None
        if time.time() - row["created_at"] > _CODE_TTL_SEC:
            return None
        conn.execute("UPDATE oauth_codes SET used = 1 WHERE code = ?", (code,))
    return dict(row)
