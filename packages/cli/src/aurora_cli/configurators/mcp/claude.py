"""Claude Code MCP server configurator.

Configures Aurora's MCP server for Claude Code CLI.

Configuration paths:
- MCP server: ~/.claude/plugins/aurora/.mcp.json
- Permissions: ~/.claude/settings.local.json
"""

import json
from pathlib import Path
from typing import Any

from aurora_cli.configurators.mcp.base import ConfigResult, MCPConfigurator

# Aurora MCP tool permissions for Claude Code
# Deprecated tools removed (aurora_query, aurora_search, aurora_get) per PRD-0024
# Use slash commands (/aur:search, /aur:get) or CLI commands (aur soar) instead
AURORA_MCP_PERMISSIONS = [
    "mcp__aurora__aurora_index",
    "mcp__aurora__aurora_context",
    "mcp__aurora__aurora_related",
    "mcp__aurora__aurora_list_agents",
    "mcp__aurora__aurora_search_agents",
    "mcp__aurora__aurora_show_agent",
]


class ClaudeMCPConfigurator(MCPConfigurator):
    """MCP configurator for Claude Code CLI.

    Claude Code uses a plugin-based MCP configuration:
    - MCP config: ~/.claude/plugins/aurora/.mcp.json
    - Permissions: ~/.claude/settings.local.json

    This configurator handles both files.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "claude"

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Claude Code"

    @property
    def is_global(self) -> bool:
        """Claude MCP config is user-level (global)."""
        return True

    def get_config_path(self, _project_path: Path) -> Path:
        """Get Claude MCP config path.

        Args:
            project_path: Project path (not used for global config)

        Returns:
            Path to ~/.claude/plugins/aurora/.mcp.json

        """
        return Path.home() / ".claude" / "plugins" / "aurora" / ".mcp.json"

    def get_permissions_path(self) -> Path:
        """Get Claude permissions config path.

        Returns:
            Path to ~/.claude/settings.local.json

        """
        return Path.home() / ".claude" / "settings.local.json"

    def get_server_config(self, project_path: Path) -> dict[str, Any]:
        """Get Aurora MCP server configuration for Claude.

        Args:
            project_path: Path to project root

        Returns:
            Dictionary with Aurora server configuration

        """
        db_path = project_path / ".aurora" / "memory.db"

        # Build PYTHONPATH for aurora packages
        # Try to find aurora source directories
        pythonpath_parts = []

        # Check if we're in the aurora project directory
        aurora_src = project_path / "src"
        aurora_packages = project_path / "packages"

        if aurora_src.exists():
            pythonpath_parts.append(str(aurora_src))

        if aurora_packages.exists():
            for pkg_dir in ["cli", "core", "context-code"]:
                pkg_src = aurora_packages / pkg_dir / "src"
                if pkg_src.exists():
                    pythonpath_parts.append(str(pkg_src))

        # Fallback: use aurora-mcp if no source found (installed package)
        if not pythonpath_parts:
            return {
                "mcpServers": {
                    "aurora": {
                        "type": "stdio",
                        "command": "aurora-mcp",
                        "args": [],
                        "env": {
                            "AURORA_DB_PATH": str(db_path),
                        },
                    },
                },
            }

        # Use python with module path for development
        return {
            "mcpServers": {
                "aurora": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["-m", "aurora_mcp.server"],
                    "env": {
                        "PYTHONPATH": ":".join(pythonpath_parts),
                        "AURORA_DB_PATH": str(db_path),
                    },
                },
            },
        }

    def configure_permissions(self, _project_path: Path) -> ConfigResult:
        """Configure Claude permissions to allow Aurora MCP tools.

        Updates ~/.claude/settings.local.json to add Aurora tool permissions.

        Args:
            project_path: Path to project root (not used for global config)

        Returns:
            ConfigResult with operation status

        """
        permissions_path = self.get_permissions_path()
        warnings: list[str] = []
        created = not permissions_path.exists()

        try:
            # Load existing settings or start fresh
            existing_settings: dict[str, Any] = {}
            if permissions_path.exists():
                try:
                    content = permissions_path.read_text(encoding="utf-8")
                    existing_settings = json.loads(content) if content.strip() else {}
                except json.JSONDecodeError as e:
                    warnings.append(f"Existing settings had invalid JSON: {e}")
                    backup_path = permissions_path.with_suffix(".json.bak")
                    permissions_path.rename(backup_path)
                    warnings.append(f"Created backup at {backup_path}")

            # Ensure permissions structure exists
            if "permissions" not in existing_settings:
                existing_settings["permissions"] = {}
            if "allow" not in existing_settings["permissions"]:
                existing_settings["permissions"]["allow"] = []

            # Get current allowed permissions
            current_allow = existing_settings["permissions"]["allow"]

            # Add Aurora permissions if not already present
            added_count = 0
            for perm in AURORA_MCP_PERMISSIONS:
                if perm not in current_allow:
                    current_allow.append(perm)
                    added_count += 1

            # Ensure parent directory exists
            permissions_path.parent.mkdir(parents=True, exist_ok=True)

            # Write updated settings
            permissions_path.write_text(
                json.dumps(existing_settings, indent=2) + "\n",
                encoding="utf-8",
            )

            if added_count > 0:
                action = "Created" if created else "Updated"
                message = f"{action} permissions ({added_count} Aurora tools added)"
            else:
                message = "Permissions already configured (no changes needed)"

            return ConfigResult(
                success=True,
                created=created,
                config_path=permissions_path,
                message=message,
                warnings=warnings,
            )

        except OSError as e:
            return ConfigResult(
                success=False,
                created=False,
                config_path=permissions_path,
                message=f"Failed to write permissions: {e}",
                warnings=warnings,
            )

    def configure(self, project_path: Path) -> ConfigResult:
        """Configure Aurora MCP server and permissions for Claude.

        Performs two operations:
        1. Creates/updates ~/.claude/plugins/aurora/.mcp.json
        2. Updates ~/.claude/settings.local.json with permissions

        Args:
            project_path: Path to project root

        Returns:
            ConfigResult with combined operation status

        """
        # First configure the MCP server
        mcp_result = super().configure(project_path)

        if not mcp_result.success:
            return mcp_result

        # Then configure permissions
        perm_result = self.configure_permissions(project_path)

        # Combine results
        if perm_result.success:
            combined_message = f"{mcp_result.message}; {perm_result.message}"
            combined_warnings = mcp_result.warnings + perm_result.warnings
        else:
            combined_message = f"{mcp_result.message}; WARNING: {perm_result.message}"
            combined_warnings = mcp_result.warnings + perm_result.warnings
            combined_warnings.append("Permissions may need manual configuration")

        return ConfigResult(
            success=mcp_result.success,  # MCP config is required, permissions are nice-to-have
            created=mcp_result.created,
            config_path=mcp_result.config_path,
            message=combined_message,
            warnings=combined_warnings,
        )

    def is_configured(self, project_path: Path) -> bool:
        """Check if Aurora MCP is configured for Claude.

        Checks both MCP config and permissions.

        Args:
            project_path: Path to project root

        Returns:
            True if both MCP config and basic permissions exist

        """
        # Check MCP config
        if not super().is_configured(project_path):
            return False

        # Check permissions (at least one Aurora permission present)
        permissions_path = self.get_permissions_path()
        if not permissions_path.exists():
            return False

        try:
            content = permissions_path.read_text(encoding="utf-8")
            settings = json.loads(content)
            allowed = settings.get("permissions", {}).get("allow", [])

            # Check if at least one Aurora permission is present
            return any(perm in allowed for perm in AURORA_MCP_PERMISSIONS)
        except (json.JSONDecodeError, OSError):
            return False
