"""Cursor MCP server configurator.

Configures Aurora's MCP server for Cursor IDE.

Configuration path: .cursor/mcp.json (project-level)
"""

from pathlib import Path

from aurora_cli.configurators.mcp.base import MCPConfigurator


class CursorMCPConfigurator(MCPConfigurator):
    """MCP configurator for Cursor IDE.

    Cursor uses project-level MCP configuration at .cursor/mcp.json.
    This allows per-project Aurora database configuration.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "cursor"

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Cursor"

    @property
    def is_global(self) -> bool:
        """Cursor MCP config is project-level."""
        return False

    def get_config_path(self, project_path: Path) -> Path:
        """Get Cursor MCP config path.

        Args:
            project_path: Path to project root

        Returns:
            Path to .cursor/mcp.json in project

        """
        return project_path / ".cursor" / "mcp.json"
