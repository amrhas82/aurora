"""Integration tests for MCP server.

These tests verify that the MCP server correctly initializes and registers tools.
Written BEFORE implementation (TDD).
"""

import pytest
from unittest.mock import Mock, patch


class TestMCPServerStartup:
    """Tests for MCP server initialization."""

    def test_mcp_server_initializes(self):
        """Test MCP server can be initialized."""
        from aurora_mcp.server import AuroraMCPServer

        # Act & Assert - should not raise
        server = AuroraMCPServer(test_mode=True)
        assert server is not None

    def test_lsp_tool_registered(self):
        """Test lsp tool is registered with MCP server."""
        from aurora_mcp.server import AuroraMCPServer

        # Act
        server = AuroraMCPServer(test_mode=True)
        tools = server.list_tools()

        # Assert
        tool_names = [tool["name"] for tool in tools]
        assert "lsp" in tool_names

    def test_mem_search_tool_registered(self):
        """Test mem_search tool is registered with MCP server."""
        from aurora_mcp.server import AuroraMCPServer

        # Act
        server = AuroraMCPServer(test_mode=True)
        tools = server.list_tools()

        # Assert
        tool_names = [tool["name"] for tool in tools]
        assert "mem_search" in tool_names

    def test_both_tools_registered(self):
        """Test both lsp and mem_search tools are registered."""
        from aurora_mcp.server import AuroraMCPServer

        # Act
        server = AuroraMCPServer(test_mode=True)
        tools = server.list_tools()

        # Assert
        tool_names = [tool["name"] for tool in tools]
        assert "lsp" in tool_names
        assert "mem_search" in tool_names
        assert len(tool_names) >= 2

    def test_lsp_tool_has_correct_metadata(self):
        """Test lsp tool has readOnlyHint and title."""
        from aurora_mcp.server import AuroraMCPServer

        # Act
        server = AuroraMCPServer(test_mode=True)
        tools = server.list_tools()

        # Assert
        lsp_tool = next((t for t in tools if t["name"] == "lsp"), None)
        assert lsp_tool is not None
        assert "readOnlyHint" in lsp_tool or "read_only" in lsp_tool
        # Tool should indicate it's read-only


class TestMCPServerToolRegistration:
    """Tests for tool registration with FastMCP."""

    @patch("aurora_mcp.server.FastMCP")
    def test_tools_registered_with_fastmcp(self, mock_fastmcp):
        """Test tools are registered using FastMCP."""
        # Arrange
        mock_mcp_instance = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        from aurora_mcp.server import AuroraMCPServer

        # Act
        server = AuroraMCPServer(test_mode=True)

        # Assert
        # FastMCP should be initialized
        mock_fastmcp.assert_called_once()


class TestMCPServerFastMCPIntegration:
    """Tests for FastMCP integration."""

    def test_server_uses_fastmcp_tool_decorator(self):
        """Test server uses @mcp.tool() decorator pattern."""
        # This is more of a structural test
        # We verify that the server module imports FastMCP
        import aurora_mcp.server as server_module

        # Assert
        assert hasattr(server_module, "FastMCP") or hasattr(server_module, "mcp")
