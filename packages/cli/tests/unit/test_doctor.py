"""Unit tests for doctor command MCP tools check.

Tests the `aur doctor` command MCP tools status check.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from aurora_cli.health_checks import ToolIntegrationChecks


class TestMCPToolsStatusCheck:
    """Test MCP tools status check in doctor command."""

    def test_mcp_tools_check_exists(self):
        """Test MCP tools check method exists."""
        from aurora_cli.config import Config

        config = Config()
        checks = ToolIntegrationChecks(config)
        assert hasattr(checks, "run_checks")

    @patch("aurora_mcp.server.AuroraMCPServer")
    def test_mcp_tools_lsp_and_mem_search_registered(self, mock_mcp_server_class):
        """Test doctor checks that lsp and mem_search tools are registered."""
        from aurora_cli.config import Config

        # Mock MCP server with lsp and mem_search tools
        mock_server = Mock()
        mock_server.list_tools.return_value = [
            {"name": "lsp"},
            {"name": "mem_search"},
            {"name": "other_tool"},
        ]
        mock_mcp_server_class.return_value = mock_server

        config = Config()
        checks = ToolIntegrationChecks(config)
        results = checks.run_checks()

        # Should have MCP tools check
        mcp_checks = [r for r in results if "mcp" in r[1].lower() and "tool" in r[1].lower()]
        assert len(mcp_checks) > 0

        # Should pass if lsp and mem_search are present
        mcp_tool_check = next(
            (r for r in results if "mcp" in r[1].lower() and "tool" in r[1].lower()), None
        )
        assert mcp_tool_check is not None
        assert mcp_tool_check[0] == "pass"  # status should be "pass"

    @patch("aurora_mcp.server.AuroraMCPServer")
    def test_mcp_tools_count_shown(self, mock_mcp_server_class):
        """Test doctor shows MCP tools count."""
        from aurora_cli.config import Config

        # Mock MCP server with 3 tools
        mock_server = Mock()
        mock_server.list_tools.return_value = [
            {"name": "lsp"},
            {"name": "mem_search"},
            {"name": "other_tool"},
        ]
        mock_mcp_server_class.return_value = mock_server

        config = Config()
        checks = ToolIntegrationChecks(config)
        results = checks.run_checks()

        # Should report tool count
        mcp_tool_check = next(
            (r for r in results if "mcp" in r[1].lower() and "tool" in r[1].lower()), None
        )
        assert mcp_tool_check is not None
        # Check metadata has count
        assert "count" in mcp_tool_check[2] or "3" in mcp_tool_check[1]

    @patch("aurora_mcp.server.AuroraMCPServer")
    def test_mcp_tools_warning_if_missing_required_tools(self, mock_mcp_server_class):
        """Test doctor shows warning if lsp or mem_search missing."""
        from aurora_cli.config import Config

        # Mock MCP server missing required tools
        mock_server = Mock()
        mock_server.list_tools.return_value = [
            {"name": "other_tool"},
        ]
        mock_mcp_server_class.return_value = mock_server

        config = Config()
        checks = ToolIntegrationChecks(config)
        results = checks.run_checks()

        # Should have warning status
        mcp_tool_check = next(
            (r for r in results if "mcp" in r[1].lower() and "tool" in r[1].lower()), None
        )
        assert mcp_tool_check is not None
        assert mcp_tool_check[0] in ["warning", "fail"]  # should warn or fail

    @patch("aurora_mcp.server.AuroraMCPServer")
    def test_mcp_tools_handles_server_error(self, mock_mcp_server_class):
        """Test doctor handles MCP server errors gracefully."""
        from aurora_cli.config import Config

        # Mock MCP server that raises error
        mock_server = Mock()
        mock_server.list_tools.side_effect = Exception("Server not available")
        mock_mcp_server_class.return_value = mock_server

        config = Config()
        checks = ToolIntegrationChecks(config)
        results = checks.run_checks()

        # Should handle error gracefully
        mcp_tool_check = next(
            (r for r in results if "mcp" in r[1].lower() and "tool" in r[1].lower()), None
        )
        assert mcp_tool_check is not None
        assert mcp_tool_check[0] in ["warning", "fail"]  # should indicate problem
