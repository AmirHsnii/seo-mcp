"""Request-scoped Google user identity for multi-tenant MCP calls."""

from __future__ import annotations

from contextvars import ContextVar

_current_google_sub: ContextVar[str | None] = ContextVar(
    "current_google_sub", default=None
)


def set_google_sub(google_sub: str | None) -> None:
    _current_google_sub.set(google_sub)


def get_google_sub() -> str | None:
    return _current_google_sub.get()
