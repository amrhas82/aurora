"""Cline MCP server configurator.

Configures Aurora's MCP server for Cline (VS Code extension).

Configuration path: .cline/mcp_servers.json (project-level)
"""

from pathlib import Path

from aurora_cli.configurators.mcp.base import MCPConfigurator


class ClineMCPConfigurator(MCPConfigurator):
    """MCP configurator for Cline VS Code extension.

    Cline uses project-level MCP configuration at .cline/mcp_servers.json.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "cline"

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Cline"

    @property
    def is_global(self) -> bool:
        """Cline MCP config is project-level."""
        return False

    def get_config_path(self, project_path: Path) -> Path:
        """Get Cline MCP config path.

        Args:
            project_path: Path to project root

        Returns:
            Path to .cline/mcp_servers.json in project

        """
        return project_path / ".cline" / "mcp_servers.json"
