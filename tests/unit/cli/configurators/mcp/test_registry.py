"""Unit tests for MCP config registry."""

from pathlib import Path

import pytest

from aurora_cli.configurators.mcp.base import MCPConfigurator
from aurora_cli.configurators.mcp.registry import MCPConfigRegistry


class MockMCPConfigurator(MCPConfigurator):
    """Mock configurator for testing."""

    def __init__(self, tool_id: str):
        self._tool_id = tool_id

    @property
    def tool_id(self) -> str:
        return self._tool_id

    @property
    def is_global(self) -> bool:
        return False

    def get_config_path(self, project_path: Path) -> Path:
        return project_path / f".{self._tool_id}" / "mcp.json"


class TestMCPConfigRegistry:
    """Tests for MCPConfigRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        MCPConfigRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        MCPConfigRegistry.clear()

    def test_register_and_get(self):
        """Can register and retrieve a configurator."""
        configurator = MockMCPConfigurator("test-tool")
        MCPConfigRegistry.register(configurator)

        retrieved = MCPConfigRegistry.get("test-tool")

        assert retrieved is not None
        assert retrieved.tool_id == "test-tool"

    def test_get_returns_none_for_unknown(self):
        """get() returns None for unregistered tool."""
        # Force initialization with real configurators
        MCPConfigRegistry._ensure_initialized()

        result = MCPConfigRegistry.get("unknown-tool")

        assert result is None

    def test_get_normalizes_tool_id(self):
        """get() normalizes tool IDs (lowercase, spaces to dashes)."""
        configurator = MockMCPConfigurator("test-tool")
        MCPConfigRegistry.register(configurator)

        # Should find with different casing
        assert MCPConfigRegistry.get("Test-Tool") is not None
        assert MCPConfigRegistry.get("TEST-TOOL") is not None

    def test_get_all_returns_list(self):
        """get_all() returns list of all configurators."""
        # Force initialization
        MCPConfigRegistry._ensure_initialized()

        all_configs = MCPConfigRegistry.get_all()

        assert isinstance(all_configs, list)
        assert len(all_configs) >= 1

    def test_get_mcp_capable_tools_returns_tool_ids(self):
        """get_mcp_capable_tools() returns list of tool IDs."""
        # Force initialization
        MCPConfigRegistry._ensure_initialized()

        tool_ids = MCPConfigRegistry.get_mcp_capable_tools()

        assert isinstance(tool_ids, list)
        assert len(tool_ids) >= 1
        assert all(isinstance(tid, str) for tid in tool_ids)

    def test_supports_mcp_returns_true_for_registered(self):
        """supports_mcp() returns True for registered tools."""
        configurator = MockMCPConfigurator("test-tool")
        MCPConfigRegistry.register(configurator)

        assert MCPConfigRegistry.supports_mcp("test-tool") is True

    def test_supports_mcp_returns_false_for_unregistered(self):
        """supports_mcp() returns False for unregistered tools."""
        MCPConfigRegistry._ensure_initialized()

        assert MCPConfigRegistry.supports_mcp("fake-tool") is False

    def test_clear_removes_all_configurators(self):
        """clear() removes all registered configurators."""
        configurator = MockMCPConfigurator("test-tool")
        MCPConfigRegistry.register(configurator)

        MCPConfigRegistry.clear()

        # After clear, should be empty (but will re-initialize on next get)
        assert len(MCPConfigRegistry._configurators) == 0
        assert MCPConfigRegistry._initialized is False


class TestMCPConfigRegistryRealConfigurators:
    """Tests that verify real configurators are registered."""

    def setup_method(self):
        """Clear and re-initialize registry."""
        MCPConfigRegistry.clear()

    def teardown_method(self):
        """Clear registry after test."""
        MCPConfigRegistry.clear()

    def test_claude_configurator_registered(self):
        """Claude configurator is registered."""
        configurator = MCPConfigRegistry.get("claude")

        assert configurator is not None
        assert configurator.tool_id == "claude"

    def test_cursor_configurator_registered(self):
        """Cursor configurator is registered."""
        configurator = MCPConfigRegistry.get("cursor")

        assert configurator is not None
        assert configurator.tool_id == "cursor"

    def test_cline_configurator_registered(self):
        """Cline configurator is registered."""
        configurator = MCPConfigRegistry.get("cline")

        assert configurator is not None
        assert configurator.tool_id == "cline"

    def test_continue_configurator_registered(self):
        """Continue configurator is registered."""
        configurator = MCPConfigRegistry.get("continue")

        assert configurator is not None
        assert configurator.tool_id == "continue"

    def test_four_mcp_tools_registered(self):
        """Exactly 4 MCP-capable tools are registered."""
        tool_ids = MCPConfigRegistry.get_mcp_capable_tools()

        assert len(tool_ids) == 4
        assert set(tool_ids) == {"claude", "cursor", "cline", "continue"}
