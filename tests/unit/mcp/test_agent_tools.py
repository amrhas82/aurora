"""Unit tests for MCP agent discovery tools.

This module tests the three new MCP tools for agent discovery:
- aurora_list_agents: List all discovered agents
- aurora_search_agents: Search agents by keyword with relevance scoring
- aurora_show_agent: Show full agent details by ID

Test Coverage:
- Success cases with valid data
- Empty results handling
- Error cases (agent not found, invalid parameters)
- JSON structure validation
- Relevance scoring algorithms
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurora_mcp.tools import AuroraMCPTools


# ==============================================================================
# Task 1.1: Tests for aurora_list_agents
# ==============================================================================


class TestAuroraListAgents:
    """Test aurora_list_agents MCP tool."""

    def test_list_agents_success_with_agents(self):
        """Should return JSON array of agents when agents are discovered."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock AgentScanner and ManifestManager
        mock_manifest = MagicMock()
        mock_manifest.agents = [
            MagicMock(
                id="qa-test-architect",
                role="Test Architect & Quality Advisor",
                source_file="/home/user/.claude/agents/qa-test-architect.md",
                when_to_use="Use for test architecture review and quality decisions",
            ),
            MagicMock(
                id="full-stack-dev",
                role="Full Stack Developer",
                source_file="/home/user/.claude/agents/full-stack-dev.md",
                when_to_use="Use for code implementation and debugging",
            ),
        ]

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_list_agents()

        # Verify JSON structure
        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 2

        # Verify first agent
        agent1 = response[0]
        assert agent1["id"] == "qa-test-architect"
        assert agent1["title"] == "Test Architect & Quality Advisor"
        assert agent1["source_path"] == "/home/user/.claude/agents/qa-test-architect.md"
        assert agent1["when_to_use"] == "Use for test architecture review and quality decisions"

        # Verify second agent
        agent2 = response[1]
        assert agent2["id"] == "full-stack-dev"
        assert agent2["title"] == "Full Stack Developer"
        assert "source_path" in agent2
        assert "when_to_use" in agent2

    def test_list_agents_empty_when_no_agents(self):
        """Should return empty array when no agents are discovered."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock empty manifest
        mock_manifest = MagicMock()
        mock_manifest.agents = []

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_list_agents()

        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 0

    def test_list_agents_json_structure_validation(self):
        """Should validate JSON structure has all required fields."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_manifest = MagicMock()
        mock_manifest.agents = [
            MagicMock(
                id="test-agent",
                role="Test Agent",
                source_file="/path/to/agent.md",
                when_to_use="Test usage",
            )
        ]

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_list_agents()

        response = json.loads(result)
        agent = response[0]

        # Verify all required fields are present
        required_fields = ["id", "title", "source_path", "when_to_use"]
        for field in required_fields:
            assert field in agent, f"Missing required field: {field}"


# ==============================================================================
# Task 1.3: Tests for aurora_search_agents
# ==============================================================================


class TestAuroraSearchAgents:
    """Test aurora_search_agents MCP tool."""

    def test_search_agents_success_with_matches(self):
        """Should return matching agents sorted by relevance score."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_manifest = MagicMock()
        mock_manifest.agents = [
            MagicMock(
                id="qa-test-architect",
                role="Test Architect & Quality Advisor",
                source_file="/path/to/qa.md",
                when_to_use="Use for test architecture review and quality decisions",
            ),
            MagicMock(
                id="full-stack-dev",
                role="Full Stack Developer",
                source_file="/path/to/dev.md",
                when_to_use="Use for code implementation and testing",
            ),
            MagicMock(
                id="product-manager",
                role="Product Manager",
                source_file="/path/to/pm.md",
                when_to_use="Use for product strategy and roadmaps",
            ),
        ]

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_search_agents("test")

        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 2  # Only qa-test-architect and full-stack-dev match

        # Verify results are sorted by relevance_score descending
        for i in range(len(response) - 1):
            assert response[i]["relevance_score"] >= response[i + 1]["relevance_score"]

        # Verify first result is qa-test-architect (best match for "test")
        assert response[0]["id"] == "qa-test-architect"
        assert response[0]["relevance_score"] > 0.0

    def test_search_agents_no_matches_returns_empty(self):
        """Should return empty array when no agents match the query."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_manifest = MagicMock()
        mock_manifest.agents = [
            MagicMock(
                id="full-stack-dev",
                role="Full Stack Developer",
                source_file="/path/to/dev.md",
                when_to_use="Use for code implementation",
            )
        ]

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_search_agents("nonexistent-keyword")

        response = json.loads(result)
        assert isinstance(response, list)
        assert len(response) == 0

    def test_search_agents_relevance_scoring_substring_matching(self):
        """Should score agents based on substring matches in id/title/when_to_use."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_manifest = MagicMock()
        mock_manifest.agents = [
            MagicMock(
                id="qa-test-architect",  # 'test' in id
                role="Quality Advisor",
                source_file="/path/to/qa.md",
                when_to_use="Use for quality",
            ),
            MagicMock(
                id="developer",
                role="Test Developer",  # 'test' in title
                source_file="/path/to/dev.md",
                when_to_use="Code implementation",
            ),
            MagicMock(
                id="reviewer",
                role="Code Reviewer",
                source_file="/path/to/rev.md",
                when_to_use="Use for testing and review",  # 'test' in when_to_use
            ),
        ]

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_search_agents("test")

        response = json.loads(result)
        assert len(response) == 3  # All match 'test'

        # Verify all have positive relevance scores
        for agent in response:
            assert 0.0 < agent["relevance_score"] <= 1.0

        # Verify id match has highest weight
        assert response[0]["id"] == "qa-test-architect"

    def test_search_agents_empty_query_validation(self):
        """Should return error JSON for empty query."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_search_agents("")

        response = json.loads(result)
        assert "error" in response
        assert "empty" in response["error"].lower()

    def test_search_agents_whitespace_query_validation(self):
        """Should return error JSON for whitespace-only query."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_search_agents("   \n\t   ")

        response = json.loads(result)
        assert "error" in response
        assert "empty" in response["error"].lower()


# ==============================================================================
# Task 1.5: Tests for aurora_show_agent
# ==============================================================================


class TestAuroraShowAgent:
    """Test aurora_show_agent MCP tool."""

    def test_show_agent_success_with_valid_id(self):
        """Should return full agent details including markdown content."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Create temporary agent file with content
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp_file:
            tmp_file.write("---\n")
            tmp_file.write("id: qa-test-architect\n")
            tmp_file.write("role: Test Architect\n")
            tmp_file.write("goal: Ensure quality\n")
            tmp_file.write("---\n")
            tmp_file.write("\n# Test Architect Agent\n\n")
            tmp_file.write("This is the full agent content.\n")
            tmp_path = tmp_file.name

        try:
            mock_manifest = MagicMock()
            mock_agent = MagicMock(
                id="qa-test-architect",
                role="Test Architect",
                source_file=tmp_path,
                when_to_use="Use for testing",
            )
            mock_manifest.agents = [mock_agent]
            mock_manifest.get_agent.return_value = mock_agent

            with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
                mock_manager = mock_manager_class.return_value
                mock_manager.get_or_refresh.return_value = mock_manifest

                result = tools.aurora_show_agent("qa-test-architect")

            response = json.loads(result)

            # Verify structure
            assert "id" in response
            assert "title" in response
            assert "source_path" in response
            assert "when_to_use" in response
            assert "content" in response

            # Verify content includes full markdown
            assert "Test Architect Agent" in response["content"]
            assert "full agent content" in response["content"]

        finally:
            Path(tmp_path).unlink()

    def test_show_agent_error_when_agent_not_found(self):
        """Should return error JSON when agent ID not found."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_manifest = MagicMock()
        mock_manifest.agents = []
        mock_manifest.get_agent.return_value = None

        with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_or_refresh.return_value = mock_manifest

            result = tools.aurora_show_agent("nonexistent-agent")

        response = json.loads(result)
        assert "error" in response
        assert response["error"] == "Agent not found"
        assert response["agent_id"] == "nonexistent-agent"

    def test_show_agent_full_content_includes_markdown(self):
        """Should include complete markdown file content in response."""
        tools = AuroraMCPTools(db_path=":memory:")

        markdown_content = """---
id: test-agent
role: Test Agent
goal: Testing
---

# Test Agent

## Overview
This is a comprehensive agent description.

## Usage
Invoke with @test-agent
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp_file:
            tmp_file.write(markdown_content)
            tmp_path = tmp_file.name

        try:
            mock_manifest = MagicMock()
            mock_agent = MagicMock(
                id="test-agent",
                role="Test Agent",
                source_file=tmp_path,
                when_to_use="For testing",
            )
            mock_manifest.agents = [mock_agent]
            mock_manifest.get_agent.return_value = mock_agent

            with patch("aurora.mcp.tools.ManifestManager") as mock_manager_class:
                mock_manager = mock_manager_class.return_value
                mock_manager.get_or_refresh.return_value = mock_manifest

                result = tools.aurora_show_agent("test-agent")

            response = json.loads(result)
            content = response["content"]

            # Verify full content is present
            assert "# Test Agent" in content
            assert "## Overview" in content
            assert "## Usage" in content
            assert "comprehensive agent description" in content

        finally:
            Path(tmp_path).unlink()

    def test_show_agent_empty_agent_id_validation(self):
        """Should return error for empty agent_id parameter."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_show_agent("")

        response = json.loads(result)
        assert "error" in response
        assert "agent_id" in response["error"].lower() or "empty" in response["error"].lower()

    def test_show_agent_whitespace_agent_id_validation(self):
        """Should return error for whitespace-only agent_id parameter."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_show_agent("   \n  ")

        response = json.loads(result)
        assert "error" in response
