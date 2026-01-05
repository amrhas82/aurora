"""Unit tests for MCP configurator base class."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from aurora_cli.configurators.mcp.base import (
    MCPConfigurator,
    ConfigResult,
    merge_mcp_config,
)


class TestMerge_mcp_config:
    """Tests for merge_mcp_config function."""

    def test_merge_empty_existing(self):
        """Merge into empty config creates mcpServers with aurora."""
        existing = {}
        aurora = {"aurora": {"command": "python3", "args": ["-m", "test"]}}

        result = merge_mcp_config(existing, aurora)

        assert "mcpServers" in result
        assert "aurora" in result["mcpServers"]
        assert result["mcpServers"]["aurora"]["command"] == "python3"

    def test_merge_preserves_existing_servers(self):
        """Merge preserves other servers in mcpServers."""
        existing = {
            "mcpServers": {
                "other-server": {"command": "node", "args": ["server.js"]},
            }
        }
        aurora = {"aurora": {"command": "python3", "args": ["-m", "aurora.mcp.server"]}}

        result = merge_mcp_config(existing, aurora)

        assert "other-server" in result["mcpServers"]
        assert "aurora" in result["mcpServers"]
        assert result["mcpServers"]["other-server"]["command"] == "node"

    def test_merge_updates_existing_aurora(self):
        """Merge updates existing aurora config."""
        existing = {
            "mcpServers": {
                "aurora": {"command": "old-python", "args": ["old"]},
            }
        }
        aurora = {"aurora": {"command": "python3", "args": ["-m", "aurora.mcp.server"]}}

        result = merge_mcp_config(existing, aurora)

        assert result["mcpServers"]["aurora"]["command"] == "python3"
        assert result["mcpServers"]["aurora"]["args"] == ["-m", "aurora.mcp.server"]

    def test_merge_handles_wrapped_format(self):
        """Merge handles aurora config wrapped in mcpServers."""
        existing = {}
        aurora = {
            "mcpServers": {
                "aurora": {"command": "python3", "args": ["-m", "test"]}
            }
        }

        result = merge_mcp_config(existing, aurora)

        assert result["mcpServers"]["aurora"]["command"] == "python3"

    def test_merge_preserves_other_top_level_keys(self):
        """Merge preserves non-mcpServers keys in existing config."""
        existing = {
            "mcpServers": {},
            "otherSetting": "value",
            "version": "1.0",
        }
        aurora = {"aurora": {"command": "python3"}}

        result = merge_mcp_config(existing, aurora)

        assert result["otherSetting"] == "value"
        assert result["version"] == "1.0"


class TestConfigResult:
    """Tests for ConfigResult dataclass."""

    def test_config_result_defaults(self):
        """ConfigResult has empty warnings by default."""
        result = ConfigResult(
            success=True,
            created=True,
            config_path=Path("/test/path"),
            message="Test message",
        )

        assert result.warnings == []

    def test_config_result_with_warnings(self):
        """ConfigResult can have warnings."""
        result = ConfigResult(
            success=True,
            created=False,
            config_path=Path("/test/path"),
            message="Test",
            warnings=["Warning 1", "Warning 2"],
        )

        assert len(result.warnings) == 2


class ConcreteMCPConfigurator(MCPConfigurator):
    """Concrete implementation for testing abstract base class."""

    def __init__(self, tool_id: str = "test-tool", is_global: bool = False):
        self._tool_id = tool_id
        self._is_global = is_global

    @property
    def tool_id(self) -> str:
        return self._tool_id

    @property
    def is_global(self) -> bool:
        return self._is_global

    def get_config_path(self, project_path: Path) -> Path:
        if self._is_global:
            return Path.home() / ".test-tool" / "mcp.json"
        return project_path / ".test-tool" / "mcp.json"


class TestMCPConfiguratorBase:
    """Tests for MCPConfigurator base class."""

    def test_name_default_from_tool_id(self):
        """Default name is derived from tool_id."""
        configurator = ConcreteMCPConfigurator(tool_id="my-tool")
        assert configurator.name == "My Tool"

    def test_name_handles_dashes(self):
        """Name converts dashes to spaces and title cases."""
        configurator = ConcreteMCPConfigurator(tool_id="github-copilot")
        assert configurator.name == "Github Copilot"

    def test_get_server_config_default(self):
        """Default server config has aurora entry with project db path."""
        configurator = ConcreteMCPConfigurator()
        project_path = Path("/test/project")

        config = configurator.get_server_config(project_path)

        assert "aurora" in config
        assert config["aurora"]["command"] == "python3"
        assert config["aurora"]["args"] == ["-m", "aurora.mcp.server"]
        assert "AURORA_DB_PATH" in config["aurora"]["env"]
        assert "/test/project/.aurora/memory.db" in config["aurora"]["env"]["AURORA_DB_PATH"]

    def test_is_configured_returns_false_when_no_file(self, tmp_path):
        """is_configured returns False when config file doesn't exist."""
        configurator = ConcreteMCPConfigurator()

        assert configurator.is_configured(tmp_path) is False

    def test_is_configured_returns_false_when_no_aurora(self, tmp_path):
        """is_configured returns False when aurora not in config."""
        configurator = ConcreteMCPConfigurator()
        config_path = tmp_path / ".test-tool" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({"mcpServers": {"other": {}}}))

        assert configurator.is_configured(tmp_path) is False

    def test_is_configured_returns_true_when_aurora_present(self, tmp_path):
        """is_configured returns True when aurora is in mcpServers."""
        configurator = ConcreteMCPConfigurator()
        config_path = tmp_path / ".test-tool" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({
            "mcpServers": {"aurora": {"command": "python3"}}
        }))

        assert configurator.is_configured(tmp_path) is True

    def test_configure_creates_new_file(self, tmp_path):
        """configure creates new config file when none exists."""
        configurator = ConcreteMCPConfigurator()

        result = configurator.configure(tmp_path)

        assert result.success is True
        assert result.created is True
        config_path = tmp_path / ".test-tool" / "mcp.json"
        assert config_path.exists()

        config = json.loads(config_path.read_text())
        assert "mcpServers" in config
        assert "aurora" in config["mcpServers"]

    def test_configure_updates_existing_file(self, tmp_path):
        """configure updates existing config, preserving other servers."""
        configurator = ConcreteMCPConfigurator()
        config_path = tmp_path / ".test-tool" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({
            "mcpServers": {"other": {"command": "node"}},
            "setting": "value",
        }))

        result = configurator.configure(tmp_path)

        assert result.success is True
        assert result.created is False

        config = json.loads(config_path.read_text())
        assert "other" in config["mcpServers"]
        assert "aurora" in config["mcpServers"]
        assert config["setting"] == "value"

    def test_configure_handles_invalid_json(self, tmp_path):
        """configure handles existing file with invalid JSON."""
        configurator = ConcreteMCPConfigurator()
        config_path = tmp_path / ".test-tool" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("{ invalid json }")

        result = configurator.configure(tmp_path)

        assert result.success is True
        assert len(result.warnings) >= 1
        assert any("invalid JSON" in w for w in result.warnings)

        # Backup should be created
        backup_path = config_path.with_suffix(".json.bak")
        assert backup_path.exists()

    def test_configure_permissions_returns_none_by_default(self, tmp_path):
        """configure_permissions returns None by default (no permissions needed)."""
        configurator = ConcreteMCPConfigurator()

        result = configurator.configure_permissions(tmp_path)

        assert result is None
