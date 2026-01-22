"""Integration tests for MCP agent discovery tools.

This module tests the three agent discovery MCP tools end-to-end through
the AuroraMCPServer instance, verifying real-world integration scenarios.

Test Coverage:
- End-to-end tool invocation through AuroraMCPServer
- Real agent file discovery and parsing
- JSON response validation
- Error handling with real file system operations
"""

import json
import tempfile
from pathlib import Path

import pytest

from aurora_mcp.server import AuroraMCPServer


# Skip all tests in this file - MCP functionality is dormant (PRD-0024)
pytestmark = pytest.mark.skip(reason="MCP functionality dormant - tests deprecated (PRD-0024)")


class TestAgentToolsIntegration:
    """Integration tests for agent discovery MCP tools."""

    @pytest.fixture
    def temp_agent_dir(self, tmp_path):
        """Create temporary agent directory with test agents."""
        agent_dir = tmp_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)

        # Create test agent files
        qa_agent = agent_dir / "quality-assurance.md"
        qa_agent.write_text(
            """---
id: quality-assurance
role: Test Architect & Quality Advisor
goal: Ensure comprehensive test coverage
category: qa
when_to_use: Use for test architecture review and quality decisions
---

# Test Architect Agent

This agent provides comprehensive test architecture guidance.

## Responsibilities
- Test strategy design
- Coverage analysis
- Quality gate decisions
"""
        )

        dev_agent = agent_dir / "code-developer.md"
        dev_agent.write_text(
            """---
id: code-developer
role: Full Stack Developer
goal: Implement features and fix bugs
category: eng
when_to_use: Use for code implementation and debugging
---

# Full Stack Developer

Expert in building full-stack applications.

## Skills
- Frontend development
- Backend services
- Database design
"""
        )

        return agent_dir

    @pytest.fixture
    def mcp_server(self, temp_agent_dir):
        """Create MCP server instance with test mode enabled."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Initialize server in test mode (skip FastMCP initialization)
        server = AuroraMCPServer(db_path=db_path, test_mode=True)

        yield server

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_aurora_list_agents_integration(self, mcp_server, temp_agent_dir, monkeypatch):
        """Test aurora_list_agents end-to-end through MCP server."""
        # Mock home directory to use temp agent dir
        monkeypatch.setenv("HOME", str(temp_agent_dir.parent.parent))

        result = mcp_server.tools.aurora_list_agents()

        # Verify JSON structure
        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 2

        # Verify agents are present
        agent_ids = {agent["id"] for agent in response}
        assert "quality-assurance" in agent_ids
        assert "code-developer" in agent_ids

        # Verify required fields
        for agent in response:
            assert "id" in agent
            assert "title" in agent
            assert "source_path" in agent
            assert "when_to_use" in agent

    def test_aurora_search_agents_integration(self, mcp_server, temp_agent_dir, monkeypatch):
        """Test aurora_search_agents end-to-end with real file discovery."""
        # Mock home directory
        monkeypatch.setenv("HOME", str(temp_agent_dir.parent.parent))

        # Search for "test" keyword
        result = mcp_server.tools.aurora_search_agents("test")

        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 1  # Only quality-assurance should match

        # Verify the matching agent
        agent = response[0]
        assert agent["id"] == "quality-assurance"
        assert "relevance_score" in agent
        assert agent["relevance_score"] > 0.0

    def test_aurora_show_agent_integration(self, mcp_server, temp_agent_dir, monkeypatch):
        """Test aurora_show_agent end-to-end with real file reading."""
        # Mock home directory
        monkeypatch.setenv("HOME", str(temp_agent_dir.parent.parent))

        # Get specific agent
        result = mcp_server.tools.aurora_show_agent("code-developer")

        response = json.loads(result)

        # Verify structure
        assert "id" in response
        assert response["id"] == "code-developer"
        assert "title" in response
        assert "content" in response

        # Verify content includes full markdown
        assert "# Full Stack Developer" in response["content"]
        assert "Frontend development" in response["content"]

    def test_aurora_show_agent_not_found_integration(self, mcp_server, temp_agent_dir, monkeypatch):
        """Test aurora_show_agent error handling for non-existent agent."""
        # Mock home directory
        monkeypatch.setenv("HOME", str(temp_agent_dir.parent.parent))

        result = mcp_server.tools.aurora_show_agent("nonexistent-agent")

        response = json.loads(result)
        assert "error" in response
        assert response["error"] == "Agent not found"
        assert response["agent_id"] == "nonexistent-agent"

    def test_aurora_search_agents_empty_query_integration(self, mcp_server):
        """Test aurora_search_agents validation with empty query."""
        result = mcp_server.tools.aurora_search_agents("")

        response = json.loads(result)
        assert "error" in response
        assert "empty" in response["error"].lower()

    def test_mcp_server_lists_agent_tools(self, mcp_server, capsys):
        """Test that MCP server list_tools includes new agent tools."""
        mcp_server.list_tools()

        captured = capsys.readouterr()
        assert "aurora_list_agents" in captured.out
        assert "aurora_search_agents" in captured.out
        assert "aurora_show_agent" in captured.out

    def test_agent_tools_with_no_agents(self, tmp_path, monkeypatch):
        """Test agent tools when no agent directories exist."""
        # Create empty home directory
        empty_home = tmp_path / "empty_home"
        empty_home.mkdir()
        monkeypatch.setenv("HOME", str(empty_home))

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            server = AuroraMCPServer(db_path=db_path, test_mode=True)

            # List agents should return empty array
            result = server.tools.aurora_list_agents()
            response = json.loads(result)
            assert isinstance(response, list)
            assert len(response) == 0

            # Search should return empty array
            result = server.tools.aurora_search_agents("anything")
            response = json.loads(result)
            assert isinstance(response, list)
            assert len(response) == 0

            # Show agent should return error
            result = server.tools.aurora_show_agent("any-agent")
            response = json.loads(result)
            assert "error" in response

        finally:
            Path(db_path).unlink(missing_ok=True)
