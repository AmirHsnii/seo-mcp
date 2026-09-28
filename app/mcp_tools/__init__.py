"""Registers every MCP tool on the shared FastMCP instance.

Each tool module in this package exposes a ``register(mcp)`` function that adds
its tool(s) to the shared server. ``register_tools`` is the single entry point
called from ``app.main``; it fans out to each module so wiring stays in one
place and adding a tool is a one-line change here.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_tools import (
    content,
    inspection,
    search_analytics,
    sitemap,
    sites,
)

# Modules registered in a stable, readable order. Each must expose register().
_TOOL_MODULES = (
    sites,
    search_analytics,
    inspection,
    sitemap,
    content,
)


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the given FastMCP instance."""
    for module in _TOOL_MODULES:
        module.register(mcp)
