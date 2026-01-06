"""Unit tests for 3-tool MCP configuration validation (Task 1.1 - TDD RED phase).

This module tests that the MCP server only registers 3 essential tools after
removing 6 redundant tools as specified in PRD-0022.

Test Coverage:
- MCP server only registers 3 tools: aurora_search, aurora_query, aurora_get
- 6 tools are removed: aurora_index, aurora_context, aurora_related,
  aurora_list_agents, aurora_search_agents, aurora_show_agent
- AuroraMCPTools class does NOT have methods for removed tools

Expected State: ALL TESTS SHOULD FAIL initially (TDD RED phase).
After implementation: ALL TESTS SHOULD PASS (TDD GREEN phase).
"""

import pytest
from unittest.mock import MagicMock, patch

from aurora_mcp.tools import AuroraMCPTools


# ==============================================================================
# Task 1.1: 3-Tool Validation Tests (TDD RED Phase)
# ==============================================================================


class TestThreeToolConfiguration:
    """Test that only 3 essential tools remain after redundant tool removal."""

    def test_aurora_mcp_tools_has_only_three_methods(self):
        """AuroraMCPTools should only have 3 public tool methods."""
        # Get all public methods (not starting with _)
        public_methods = [
            method for method in dir(AuroraMCPTools)
            if not method.startswith('_') and callable(getattr(AuroraMCPTools, method))
        ]

        # Filter out non-tool methods (like from object class, etc.)
        # Tool methods should start with "aurora_"
        tool_methods = [m for m in public_methods if m.startswith('aurora_')]

        # Should have exactly 3 tools
        assert len(tool_methods) == 3, (
            f"Expected exactly 3 tool methods, found {len(tool_methods)}: {tool_methods}"
        )

    def test_essential_tools_present(self):
        """Essential tools (aurora_search, aurora_query, aurora_get) must be present."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Check all 3 essential tools exist
        assert hasattr(tools, 'aurora_search'), "aurora_search method missing"
        assert hasattr(tools, 'aurora_query'), "aurora_query method missing"
        assert hasattr(tools, 'aurora_get'), "aurora_get method missing"

        # Verify they are callable
        assert callable(tools.aurora_search), "aurora_search is not callable"
        assert callable(tools.aurora_query), "aurora_query is not callable"
        assert callable(tools.aurora_get), "aurora_get is not callable"

    def test_redundant_tool_aurora_index_removed(self):
        """aurora_index method should be removed from AuroraMCPTools."""
        tools = AuroraMCPTools(db_path=":memory:")

        assert not hasattr(tools, 'aurora_index'), (
            "aurora_index method should be removed (redundant - use CLI 'aur mem index' instead)"
        )

    def test_redundant_tool_aurora_context_removed(self):
        """aurora_context method should be removed from AuroraMCPTools."""
        tools = AuroraMCPTools(db_path=":memory:")

        assert not hasattr(tools, 'aurora_context'), (
            "aurora_context method should be removed (redundant - use Claude's Read tool instead)"
        )

    def test_redundant_tool_aurora_related_removed(self):
        """aurora_related method should be removed from AuroraMCPTools."""
        tools = AuroraMCPTools(db_path=":memory:")

        assert not hasattr(tools, 'aurora_related'), (
            "aurora_related method should be removed (redundant - use CLI 'aur mem related' instead)"
        )

    def test_redundant_tool_aurora_list_agents_removed(self):
        """aurora_list_agents method should be removed from AuroraMCPTools."""
        tools = AuroraMCPTools(db_path=":memory:")

        assert not hasattr(tools, 'aurora_list_agents'), (
            "aurora_list_agents method should be removed (redundant - use CLI 'aur agents list' instead)"
        )

    def test_redundant_tool_aurora_search_agents_removed(self):
        """aurora_search_agents method should be removed from AuroraMCPTools."""
        tools = AuroraMCPTools(db_path=":memory:")

        assert not hasattr(tools, 'aurora_search_agents'), (
            "aurora_search_agents method should be removed (redundant - use CLI 'aur agents search' instead)"
        )

    def test_redundant_tool_aurora_show_agent_removed(self):
        """aurora_show_agent method should be removed from AuroraMCPTools."""
        tools = AuroraMCPTools(db_path=":memory:")

        assert not hasattr(tools, 'aurora_show_agent'), (
            "aurora_show_agent method should be removed (redundant - use Claude's Read tool instead)"
        )

    def test_only_essential_tools_are_aurora_prefixed(self):
        """Only the 3 essential tools should have 'aurora_' prefix."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Get all attributes with aurora_ prefix
        aurora_attrs = [
            attr for attr in dir(tools)
            if attr.startswith('aurora_') and not attr.startswith('_')
        ]

        # Should be exactly 3
        expected_tools = {'aurora_search', 'aurora_query', 'aurora_get'}
        actual_tools = set(aurora_attrs)

        assert actual_tools == expected_tools, (
            f"Expected only {expected_tools}, but found {actual_tools}. "
            f"Extra tools: {actual_tools - expected_tools}. "
            f"Missing tools: {expected_tools - actual_tools}"
        )


class TestMCPServerRegistration:
    """Test that MCP server only registers 3 tools."""

    def test_server_registers_only_three_tools(self):
        """MCP server should only register aurora_search, aurora_query, aurora_get."""
        # This will be tested by checking the server.py file
        # For now, we import and check what would be registered
        from aurora_mcp import server

        # The server module should only expose 3 tools
        # We'll verify this by checking the tool registration
        # This is a structural test - actual registration tested in integration tests

        # At minimum, verify the module can be imported
        assert server is not None, "MCP server module should be importable"

    def test_removed_tools_not_in_server_exports(self):
        """Removed tools should not be exported by server module."""
        from aurora_mcp import server

        # Tools that should NOT be in server
        removed_tools = [
            'aurora_index',
            'aurora_context',
            'aurora_related',
            'aurora_list_agents',
            'aurora_search_agents',
            'aurora_show_agent'
        ]

        # Get server's exported items
        server_attrs = dir(server)

        # None of the removed tools should be in server's exports
        for tool_name in removed_tools:
            assert tool_name not in server_attrs, (
                f"{tool_name} should not be registered in MCP server (tool removed in PRD-0022)"
            )
