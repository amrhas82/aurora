"""Base class for MCP server configurators.

Defines the interface that all tool-specific MCP configurators must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass
class ConfigResult:
    """Result of an MCP configuration operation.

    Attributes:
        success: Whether the configuration succeeded
        created: Whether a new config file was created (vs updated)
        config_path: Path to the config file that was modified
        message: Human-readable status message
        warnings: List of warning messages (non-fatal issues)
    """

    success: bool
    created: bool
    config_path: Path
    message: str
    warnings: list[str] = field(default_factory=list)


def merge_mcp_config(existing: dict[str, Any], aurora_config: dict[str, Any]) -> dict[str, Any]:
    """Safely merge Aurora MCP config into existing config.

    Preserves all existing servers and settings, only adds/updates the
    'aurora' server entry.

    Args:
        existing: Existing MCP configuration (may be empty)
        aurora_config: Aurora server configuration to add/update

    Returns:
        Merged configuration dictionary

    Example:
        >>> existing = {"mcpServers": {"other": {...}}}
        >>> aurora = {"aurora": {"command": "python3", ...}}
        >>> merge_mcp_config(existing, aurora)
        {"mcpServers": {"other": {...}, "aurora": {...}}}
    """
    result = existing.copy()

    # Ensure mcpServers key exists
    if "mcpServers" not in result:
        result["mcpServers"] = {}

    # Handle both formats: direct server config or wrapped in mcpServers
    if "aurora" in aurora_config:
        # Direct format: {"aurora": {...}}
        result["mcpServers"]["aurora"] = aurora_config["aurora"]
    elif "mcpServers" in aurora_config and "aurora" in aurora_config["mcpServers"]:
        # Wrapped format: {"mcpServers": {"aurora": {...}}}
        result["mcpServers"]["aurora"] = aurora_config["mcpServers"]["aurora"]

    return result


class MCPConfigurator(ABC):
    """Abstract base for tool-specific MCP server configurators.

    Each AI coding tool (Claude Code, Cursor, etc.) that supports MCP
    has its own configurator that knows how to configure the MCP server
    for that tool.
    """

    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Tool identifier (e.g., 'claude', 'cursor').

        Must match the corresponding SlashCommandConfigurator.tool_id
        for tools that have both.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable tool name.

        Defaults to capitalizing the tool_id. Override in subclasses
        for custom display names.
        """
        return self.tool_id.replace("-", " ").title()

    @property
    @abstractmethod
    def is_global(self) -> bool:
        """Whether config is user-level (True) or project-level (False).

        Global configs (like Claude's ~/.claude/plugins/) are configured once
        per user. Project configs (like Cursor's .cursor/mcp.json) are
        configured per-project.
        """
        ...

    @abstractmethod
    def get_config_path(self, project_path: Path) -> Path:
        """Get the path to the MCP config file.

        Args:
            project_path: Path to project root (used for project-level configs)

        Returns:
            Path to the MCP configuration file
        """
        ...

    def get_server_config(self, project_path: Path) -> dict[str, Any]:
        """Get the Aurora MCP server configuration.

        Args:
            project_path: Path to project root

        Returns:
            Dictionary with Aurora server configuration

        Note:
            Default implementation returns standard Aurora MCP server config.
            Override in subclasses for tool-specific formats.
        """
        db_path = project_path / ".aurora" / "memory.db"

        return {
            "aurora": {
                "command": "python3",
                "args": ["-m", "aurora.mcp.server"],
                "env": {
                    "AURORA_DB_PATH": str(db_path),
                },
            }
        }

    def is_configured(self, project_path: Path) -> bool:
        """Check if Aurora MCP server is already configured.

        Args:
            project_path: Path to project root

        Returns:
            True if Aurora is configured in MCP config
        """
        config_path = self.get_config_path(project_path)

        if not config_path.exists():
            return False

        try:
            content = config_path.read_text(encoding="utf-8")
            config = json.loads(content)

            # Check for Aurora in mcpServers
            if "mcpServers" in config and "aurora" in config["mcpServers"]:
                return True

            # Also check direct format (some tools use this)
            if "aurora" in config:
                return True

            return False
        except (json.JSONDecodeError, OSError):
            return False

    def configure(self, project_path: Path) -> ConfigResult:
        """Configure Aurora MCP server for this tool.

        Creates or updates the MCP configuration file with Aurora server.

        Args:
            project_path: Path to project root

        Returns:
            ConfigResult with operation status
        """
        config_path = self.get_config_path(project_path)
        warnings: list[str] = []
        created = not config_path.exists()

        try:
            # Load existing config or start fresh
            existing_config: dict[str, Any] = {}
            if config_path.exists():
                try:
                    content = config_path.read_text(encoding="utf-8")
                    existing_config = json.loads(content) if content.strip() else {}
                except json.JSONDecodeError as e:
                    warnings.append(f"Existing config had invalid JSON: {e}")
                    # Create backup before overwriting
                    backup_path = config_path.with_suffix(".json.bak")
                    config_path.rename(backup_path)
                    warnings.append(f"Created backup at {backup_path}")

            # Get Aurora server config
            aurora_config = self.get_server_config(project_path)

            # Merge configs
            merged_config = merge_mcp_config(existing_config, aurora_config)

            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write merged config
            config_path.write_text(
                json.dumps(merged_config, indent=2) + "\n",
                encoding="utf-8",
            )

            action = "Created" if created else "Updated"
            return ConfigResult(
                success=True,
                created=created,
                config_path=config_path,
                message=f"{action} MCP config at {config_path}",
                warnings=warnings,
            )

        except OSError as e:
            return ConfigResult(
                success=False,
                created=False,
                config_path=config_path,
                message=f"Failed to write MCP config: {e}",
                warnings=warnings,
            )

    def configure_permissions(self, project_path: Path) -> ConfigResult | None:
        """Configure additional permissions if needed.

        Some tools (like Claude) require separate permission configuration.
        Override in subclasses that need this.

        Args:
            project_path: Path to project root

        Returns:
            ConfigResult if permissions were configured, None if not needed
        """
        return None
