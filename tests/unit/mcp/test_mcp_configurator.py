"""Unit tests for MCP configurator integration.

Tests that MCP tools are properly integrated with the configurator infrastructure.
Written BEFORE implementation (TDD).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestMCPConfiguratorIntegration:
    """Tests for MCP configurator integration."""

    def test_mcp_tools_register_with_configurator(self):
        """Test MCP tools are available through configurator."""
        from aurora_cli.configurators.mcp.registry import MCPConfigRegistry

        # Act
        configurators = MCPConfigRegistry.get_all()

        # Assert
        # Should have configurators for various tools (Claude, Cursor, Cline, Continue)
        assert len(configurators) >= 4

    def test_aurora_mcp_server_in_config(self):
        """Test Aurora MCP server configuration includes LSP tools."""
        from aurora_cli.configurators.mcp.base import merge_mcp_config

        # Arrange
        existing_config = {"mcpServers": {}}
        aurora_config = {
            "aurora": {
                "command": "python3",
                "args": ["-m", "aurora_mcp.server"],
            }
        }

        # Act
        merged = merge_mcp_config(existing_config, aurora_config)

        # Assert
        assert "mcpServers" in merged
        assert "aurora" in merged["mcpServers"]


class TestMCPConfiguratorClaudeSupport:
    """Tests for Claude Code MCP configuration."""

    @patch("aurora_cli.configurators.mcp.base.Path")
    def test_claude_configurator_exists(self, mock_path):
        """Test configurator supports Claude Code."""
        from aurora_cli.configurators.mcp.registry import MCPConfigRegistry

        # Act
        configurator = MCPConfigRegistry.get("claude")

        # Assert
        assert configurator is not None


class TestMCPConfiguratorCursorSupport:
    """Tests for Cursor MCP configuration."""

    @patch("aurora_cli.configurators.mcp.base.Path")
    def test_cursor_configurator_exists(self, mock_path):
        """Test configurator supports Cursor."""
        from aurora_cli.configurators.mcp.registry import MCPConfigRegistry

        # Act
        configurator = MCPConfigRegistry.get("cursor")

        # Assert
        assert configurator is not None


class TestMCPConfiguratorClineSupport:
    """Tests for Cline MCP configuration."""

    @patch("aurora_cli.configurators.mcp.base.Path")
    def test_cline_configurator_exists(self, mock_path):
        """Test configurator supports Cline."""
        from aurora_cli.configurators.mcp.registry import MCPConfigRegistry

        # Act
        configurator = MCPConfigRegistry.get("cline")

        # Assert
        assert configurator is not None


class TestMCPConfiguratorContinueSupport:
    """Tests for Continue MCP configuration."""

    @patch("aurora_cli.configurators.mcp.base.Path")
    def test_continue_configurator_exists(self, mock_path):
        """Test configurator supports Continue."""
        from aurora_cli.configurators.mcp.registry import MCPConfigRegistry

        # Act
        configurator = MCPConfigRegistry.get("continue")

        # Assert
        assert configurator is not None


class TestMCPServerConfiguration:
    """Tests for Aurora MCP server configuration."""

    def test_aurora_server_command_format(self):
        """Test Aurora MCP server has correct command format."""
        # This would test the actual server configuration
        # The server should be invocable via standard Python module invocation
        pass

    def test_aurora_server_includes_lsp_tools(self):
        """Test Aurora server configuration mentions LSP tools."""
        # Configuration should indicate LSP tools are available
        pass


class TestMCPToolDiscoverability:
    """Tests for MCP tool discoverability."""

    def test_lsp_tool_has_title(self):
        """Test lsp tool has title for discoverability."""
        # When implemented, lsp tool should have metadata
        # including title like "LSP Code Intelligence"
        pass

    def test_mem_search_tool_has_title(self):
        """Test mem_search tool has title for discoverability."""
        # When implemented, mem_search tool should have metadata
        pass
