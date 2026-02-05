"""MCP server configurators for AI coding tools.

This module provides configurators for setting up Aurora's MCP server
integration with various AI coding tools (Claude Code, Cursor, etc.).

MCP (Model Context Protocol) configuration is separate from slash commands:
- Slash commands: Project-level markdown files with Aurora instructions
- MCP config: JSON files that register Aurora's MCP server with tools
"""

from aurora_cli.configurators.mcp.base import ConfigResult, MCPConfigurator, merge_mcp_config
from aurora_cli.configurators.mcp.registry import MCPConfigRegistry


__all__ = [
    "MCPConfigurator",
    "MCPConfigRegistry",
    "ConfigResult",
    "merge_mcp_config",
]
