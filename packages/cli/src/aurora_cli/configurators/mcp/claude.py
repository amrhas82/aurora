"""Claude Code MCP server configurator.

Configures Aurora's MCP server for Claude Code CLI using `claude mcp add-json`.

Configuration:
- MCP server: Registered via `claude mcp add-json` command
- Permissions: ~/.claude/settings.local.json
"""

import json
import shutil
import subprocess
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

    Uses `claude mcp add-json` command to register Aurora MCP server.
    Also configures permissions in ~/.claude/settings.local.json.
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
        """Get Claude config path (for compatibility).

        Note: Claude CLI manages its own config via `claude mcp` commands.
        This returns ~/.claude.json for reference only.
        """
        return Path.home() / ".claude.json"

    def get_permissions_path(self) -> Path:
        """Get Claude permissions config path."""
        return Path.home() / ".claude" / "settings.local.json"

    def _get_server_json(self, project_path: Path) -> dict[str, Any]:
        """Get Aurora MCP server configuration as JSON for claude mcp add-json.

        Args:
            project_path: Path to project root

        Returns:
            Server configuration dict (without mcpServers wrapper)
        """
        db_path = project_path / ".aurora" / "memory.db"

        # Build PYTHONPATH for aurora packages (development mode)
        pythonpath_parts = []
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
                "command": "aurora-mcp",
                "args": [],
                "env": {
                    "AURORA_DB_PATH": str(db_path),
                },
            }

        # Use python with module path for development
        # Prefer python3.12 if available (Python 3.14 has anyio compatibility issues)
        python_cmd = "python3.12" if shutil.which("python3.12") else "python3"
        return {
            "command": python_cmd,
            "args": ["-m", "aurora_mcp.server"],
            "env": {
                "PYTHONPATH": ":".join(pythonpath_parts),
                "AURORA_DB_PATH": str(db_path),
            },
        }

    def get_server_config(self, project_path: Path) -> dict[str, Any]:
        """Get Aurora MCP server configuration (for base class compatibility)."""
        return {"mcpServers": {"aurora": self._get_server_json(project_path)}}

    def configure_permissions(self, _project_path: Path) -> ConfigResult:
        """Configure Claude permissions to allow Aurora MCP tools."""
        permissions_path = self.get_permissions_path()
        warnings: list[str] = []
        created = not permissions_path.exists()

        try:
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

            if "permissions" not in existing_settings:
                existing_settings["permissions"] = {}
            if "allow" not in existing_settings["permissions"]:
                existing_settings["permissions"]["allow"] = []

            current_allow = existing_settings["permissions"]["allow"]
            added_count = 0
            for perm in AURORA_MCP_PERMISSIONS:
                if perm not in current_allow:
                    current_allow.append(perm)
                    added_count += 1

            permissions_path.parent.mkdir(parents=True, exist_ok=True)
            permissions_path.write_text(
                json.dumps(existing_settings, indent=2) + "\n",
                encoding="utf-8",
            )

            if added_count > 0:
                action = "Created" if created else "Updated"
                message = f"{action} permissions ({added_count} Aurora tools added)"
            else:
                message = "Permissions already configured"

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
        """Configure Aurora MCP server using `claude mcp add-json`.

        Args:
            project_path: Path to project root

        Returns:
            ConfigResult with operation status
        """
        warnings: list[str] = []
        config_path = self.get_config_path(project_path)

        # Check if claude CLI is available
        if not shutil.which("claude"):
            return ConfigResult(
                success=False,
                created=False,
                config_path=config_path,
                message="Claude CLI not found in PATH",
                warnings=["Install Claude Code CLI: https://claude.ai/download"],
            )

        # Check if already configured
        was_configured = self.is_configured(project_path)

        # Remove existing aurora server if present (to update config)
        if was_configured:
            try:
                subprocess.run(
                    ["claude", "mcp", "remove", "aurora"],
                    capture_output=True,
                    text=True,
                    check=False,  # Don't fail if not found
                )
            except Exception:
                pass  # Ignore removal errors

        # Get server config and add via claude mcp add-json
        server_config = self._get_server_json(project_path)
        server_json = json.dumps(server_config)

        try:
            result = subprocess.run(
                ["claude", "mcp", "add-json", "aurora", server_json],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stderr and "error" in result.stderr.lower():
                warnings.append(result.stderr.strip())
        except subprocess.CalledProcessError as e:
            return ConfigResult(
                success=False,
                created=False,
                config_path=config_path,
                message=f"Failed to add MCP server: {e.stderr or e.stdout}",
                warnings=warnings,
            )

        # Configure permissions
        perm_result = self.configure_permissions(project_path)

        action = "Updated" if was_configured else "Added"
        combined_message = f"{action} aurora MCP server; {perm_result.message}"
        combined_warnings = warnings + perm_result.warnings

        return ConfigResult(
            success=True,
            created=not was_configured,
            config_path=config_path,
            message=combined_message,
            warnings=combined_warnings,
        )

    def is_configured(self, project_path: Path) -> bool:
        """Check if Aurora MCP is configured for Claude using `claude mcp get`."""
        if not shutil.which("claude"):
            return False

        try:
            result = subprocess.run(
                ["claude", "mcp", "get", "aurora"],
                capture_output=True,
                text=True,
                check=False,
            )
            # If aurora server exists, the command succeeds
            return result.returncode == 0 and "aurora" in result.stdout.lower()
        except Exception:
            return False
