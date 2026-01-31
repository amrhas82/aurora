"""Continue MCP server configurator.

Configures Aurora's MCP server for Continue (VS Code extension).

Configuration path: ~/.continue/config.json (global)
"""

import json
from pathlib import Path
from typing import Any

from aurora_cli.configurators.mcp.base import ConfigResult, MCPConfigurator


class ContinueMCPConfigurator(MCPConfigurator):
    """MCP configurator for Continue VS Code extension.

    Continue uses a global config at ~/.continue/config.json.
    The MCP servers are nested under the 'experimental' key.
    """

    @property
    def tool_id(self) -> str:
        """Tool identifier."""
        return "continue"

    @property
    def name(self) -> str:
        """Human-readable tool name."""
        return "Continue"

    @property
    def is_global(self) -> bool:
        """Continue config is user-level (global)."""
        return True

    def get_config_path(self, _project_path: Path) -> Path:
        """Get Continue config path.

        Args:
            project_path: Project path (not used for global config)

        Returns:
            Path to ~/.continue/config.json

        """
        return Path.home() / ".continue" / "config.json"

    def get_server_config(self, project_path: Path) -> dict[str, Any]:
        """Get Aurora MCP server configuration for Continue.

        Continue uses a different structure with 'experimental.modelContextProtocolServers'.

        Args:
            project_path: Path to project root

        Returns:
            Dictionary with Aurora server configuration

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

        # Use python with module path if source found, else fallback to aurora-mcp
        if pythonpath_parts:
            return {
                "aurora": {
                    "command": "python3",
                    "args": ["-m", "aurora_mcp.server"],
                    "env": {
                        "PYTHONPATH": ":".join(pythonpath_parts),
                        "AURORA_DB_PATH": str(db_path),
                    },
                },
            }

        return {
            "aurora": {
                "command": "aurora-mcp",
                "args": [],
                "env": {
                    "AURORA_DB_PATH": str(db_path),
                },
            },
        }

    def configure(self, project_path: Path) -> ConfigResult:
        """Configure Aurora MCP server for Continue.

        Continue stores MCP servers under 'experimental.modelContextProtocolServers'.

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
                    backup_path = config_path.with_suffix(".json.bak")
                    config_path.rename(backup_path)
                    warnings.append(f"Created backup at {backup_path}")

            # Get Aurora server config
            aurora_config = self.get_server_config(project_path)

            # Continue uses 'experimental.modelContextProtocolServers' path
            if "experimental" not in existing_config:
                existing_config["experimental"] = {}
            if "modelContextProtocolServers" not in existing_config["experimental"]:
                existing_config["experimental"]["modelContextProtocolServers"] = []

            # Check if aurora is already configured
            servers = existing_config["experimental"]["modelContextProtocolServers"]
            aurora_entry = {
                "name": "aurora",
                **aurora_config["aurora"],
            }

            # Update or add aurora entry
            aurora_index = None
            for i, server in enumerate(servers):
                if server.get("name") == "aurora":
                    aurora_index = i
                    break

            if aurora_index is not None:
                servers[aurora_index] = aurora_entry
            else:
                servers.append(aurora_entry)

            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write merged config
            config_path.write_text(
                json.dumps(existing_config, indent=2) + "\n",
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

    def is_configured(self, project_path: Path) -> bool:
        """Check if Aurora MCP server is configured for Continue.

        Args:
            project_path: Path to project root

        Returns:
            True if Aurora is in Continue's MCP servers list

        """
        config_path = self.get_config_path(project_path)

        if not config_path.exists():
            return False

        try:
            content = config_path.read_text(encoding="utf-8")
            config = json.loads(content)

            servers = config.get("experimental", {}).get("modelContextProtocolServers", [])
            return any(s.get("name") == "aurora" for s in servers)
        except (json.JSONDecodeError, OSError):
            return False
