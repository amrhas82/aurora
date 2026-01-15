"""Unit tests for Claude MCP configurator."""

import json
from pathlib import Path
from unittest.mock import patch

from aurora_cli.configurators.mcp.claude import AURORA_MCP_PERMISSIONS, ClaudeMCPConfigurator


class TestClaudeMCPConfigurator:
    """Tests for ClaudeMCPConfigurator."""

    def test_tool_id(self):
        """tool_id is 'claude'."""
        configurator = ClaudeMCPConfigurator()
        assert configurator.tool_id == "claude"

    def test_name(self):
        """name is 'Claude Code'."""
        configurator = ClaudeMCPConfigurator()
        assert configurator.name == "Claude Code"

    def test_is_global(self):
        """Claude config is global."""
        configurator = ClaudeMCPConfigurator()
        assert configurator.is_global is True

    def test_get_config_path(self, tmp_path):
        """Config path is ~/.claude/plugins/aurora/.mcp.json."""
        configurator = ClaudeMCPConfigurator()

        with patch.object(Path, "home", return_value=tmp_path):
            path = configurator.get_config_path(tmp_path)

        assert path == tmp_path / ".claude" / "plugins" / "aurora" / ".mcp.json"

    def test_get_permissions_path(self, tmp_path):
        """Permissions path is ~/.claude/settings.local.json."""
        configurator = ClaudeMCPConfigurator()

        with patch.object(Path, "home", return_value=tmp_path):
            path = configurator.get_permissions_path()

        assert path == tmp_path / ".claude" / "settings.local.json"

    def test_get_server_config(self, tmp_path):
        """Server config has aurora entry with project db path."""
        configurator = ClaudeMCPConfigurator()

        config = configurator.get_server_config(tmp_path)

        assert "mcpServers" in config
        assert "aurora" in config["mcpServers"]
        aurora_config = config["mcpServers"]["aurora"]
        assert aurora_config["command"] == "aurora-mcp"
        assert aurora_config["args"] == []
        assert str(tmp_path / ".aurora" / "memory.db") in aurora_config["env"]["AURORA_DB_PATH"]


class TestClaudeMCPConfiguratorPermissions:
    """Tests for Claude permissions configuration."""

    def test_configure_permissions_creates_new_file(self, tmp_path):
        """configure_permissions creates new settings.local.json."""
        configurator = ClaudeMCPConfigurator()

        with patch.object(Path, "home", return_value=tmp_path):
            result = configurator.configure_permissions(tmp_path)

        assert result.success is True
        assert result.created is True

        settings_path = tmp_path / ".claude" / "settings.local.json"
        assert settings_path.exists()

        settings = json.loads(settings_path.read_text())
        assert "permissions" in settings
        assert "allow" in settings["permissions"]
        # All Aurora permissions should be added
        for perm in AURORA_MCP_PERMISSIONS:
            assert perm in settings["permissions"]["allow"]

    def test_configure_permissions_preserves_existing(self, tmp_path):
        """configure_permissions preserves existing permissions."""
        configurator = ClaudeMCPConfigurator()
        settings_path = tmp_path / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True)

        existing = {
            "permissions": {
                "allow": ["Bash(*)", "Read(*)"],
            },
            "otherSetting": "value",
        }
        settings_path.write_text(json.dumps(existing))

        with patch.object(Path, "home", return_value=tmp_path):
            result = configurator.configure_permissions(tmp_path)

        assert result.success is True

        settings = json.loads(settings_path.read_text())
        # Existing permissions preserved
        assert "Bash(*)" in settings["permissions"]["allow"]
        assert "Read(*)" in settings["permissions"]["allow"]
        # Aurora permissions added
        assert AURORA_MCP_PERMISSIONS[0] in settings["permissions"]["allow"]
        # Other settings preserved
        assert settings["otherSetting"] == "value"

    def test_configure_permissions_skips_existing_aurora_perms(self, tmp_path):
        """configure_permissions doesn't duplicate existing Aurora permissions."""
        configurator = ClaudeMCPConfigurator()
        settings_path = tmp_path / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True)

        existing = {
            "permissions": {
                "allow": [AURORA_MCP_PERMISSIONS[0]],  # One already exists
            },
        }
        settings_path.write_text(json.dumps(existing))

        with patch.object(Path, "home", return_value=tmp_path):
            result = configurator.configure_permissions(tmp_path)

        assert result.success is True

        settings = json.loads(settings_path.read_text())
        # Count how many times first permission appears
        count = settings["permissions"]["allow"].count(AURORA_MCP_PERMISSIONS[0])
        assert count == 1  # Not duplicated


class TestClaudeMCPConfiguratorConfigure:
    """Tests for full Claude MCP configuration."""

    def test_configure_creates_mcp_and_permissions(self, tmp_path):
        """configure() creates both MCP config and permissions."""
        configurator = ClaudeMCPConfigurator()

        with patch.object(Path, "home", return_value=tmp_path):
            result = configurator.configure(tmp_path)

        assert result.success is True

        # MCP config created
        mcp_path = tmp_path / ".claude" / "plugins" / "aurora" / ".mcp.json"
        assert mcp_path.exists()
        mcp_config = json.loads(mcp_path.read_text())
        assert "mcpServers" in mcp_config
        assert "aurora" in mcp_config["mcpServers"]

        # Permissions created
        settings_path = tmp_path / ".claude" / "settings.local.json"
        assert settings_path.exists()


class TestClaudeMCPConfiguratorIsConfigured:
    """Tests for is_configured check."""

    def test_is_configured_false_when_no_files(self, tmp_path):
        """is_configured returns False when no files exist."""
        configurator = ClaudeMCPConfigurator()

        with patch.object(Path, "home", return_value=tmp_path):
            assert configurator.is_configured(tmp_path) is False

    def test_is_configured_false_when_mcp_only(self, tmp_path):
        """is_configured returns False when only MCP config exists."""
        configurator = ClaudeMCPConfigurator()

        # Create MCP config but not permissions
        mcp_path = tmp_path / ".claude" / "plugins" / "aurora" / ".mcp.json"
        mcp_path.parent.mkdir(parents=True)
        mcp_path.write_text(json.dumps({"mcpServers": {"aurora": {}}}))

        with patch.object(Path, "home", return_value=tmp_path):
            assert configurator.is_configured(tmp_path) is False

    def test_is_configured_true_when_both_exist(self, tmp_path):
        """is_configured returns True when MCP and permissions exist."""
        configurator = ClaudeMCPConfigurator()

        # Create MCP config with valid aurora-mcp command
        mcp_path = tmp_path / ".claude" / "plugins" / "aurora" / ".mcp.json"
        mcp_path.parent.mkdir(parents=True)
        mcp_path.write_text(
            json.dumps({"mcpServers": {"aurora": {"command": "aurora-mcp", "args": []}}})
        )

        # Create permissions with Aurora permission
        settings_path = tmp_path / ".claude" / "settings.local.json"
        settings_path.write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": [AURORA_MCP_PERMISSIONS[0]],
                    }
                }
            )
        )

        with patch.object(Path, "home", return_value=tmp_path):
            assert configurator.is_configured(tmp_path) is True
