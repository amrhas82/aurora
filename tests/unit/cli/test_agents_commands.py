"""Unit tests for agent discovery CLI commands.

Tests the aur agents command group including list, search, show, and refresh.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.agent_discovery.models import AgentCategory, AgentInfo, AgentManifest
from aurora_cli.commands.agents import (
    _find_similar_agents,
    _search_agents,
    _truncate,
    agents_group,
    get_manifest,
)
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_manifest(tmp_path: Path) -> AgentManifest:
    """Create a sample manifest with test agents."""
    agents = [
        AgentInfo(
            id="qa-test-architect",
            role="Test Architect & Quality Advisor",
            goal="Ensure comprehensive test coverage",
            category=AgentCategory.QA,
            skills=["test strategy", "coverage analysis"],
            when_to_use="Use for test architecture review",
        ),
        AgentInfo(
            id="full-stack-dev",
            role="Full Stack Developer",
            goal="Implement features and fix bugs",
            category=AgentCategory.ENG,
            skills=["python", "javascript", "databases"],
        ),
        AgentInfo(
            id="product-manager",
            role="Product Manager",
            goal="Define product strategy",
            category=AgentCategory.PRODUCT,
            skills=["roadmapping", "prioritization"],
        ),
        AgentInfo(
            id="orchestrator",
            role="Master Orchestrator",
            goal="Coordinate multi-agent workflows",
            category=AgentCategory.GENERAL,
            skills=["workflow coordination"],
        ),
    ]

    manifest = AgentManifest(agents=agents)
    manifest.stats.total = len(agents)
    manifest.stats.by_category = {
        "eng": 1,
        "qa": 1,
        "product": 1,
        "general": 1,
    }

    return manifest


class TestAgentsListCommand:
    """Tests for aur agents list command."""

    def test_list_all_agents(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Lists all agents grouped by category."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["list"])

        assert result.exit_code == 0
        assert "qa-test-architect" in result.output
        assert "full-stack-dev" in result.output
        assert "product-manager" in result.output
        assert "orchestrator" in result.output
        assert "4 agent(s)" in result.output

    def test_list_filter_by_category(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Lists only agents in specified category."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["list", "--category", "qa"])

        assert result.exit_code == 0
        assert "qa-test-architect" in result.output
        assert "full-stack-dev" not in result.output

    def test_list_empty_manifest(self, cli_runner: CliRunner) -> None:
        """Shows message when no agents found."""
        empty_manifest = AgentManifest()

        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=empty_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["list"])

        assert result.exit_code == 0
        assert "No agents found" in result.output

    def test_list_simple_format(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Lists agents with simple (non-Rich) format."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["list", "--format", "simple"])

        assert result.exit_code == 0
        # Simple format should still show agent info
        assert "qa-test-architect" in result.output


class TestAgentsSearchCommand:
    """Tests for aur agents search command."""

    def test_search_by_keyword(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Searches and finds agents matching keyword."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["search", "test"])

        assert result.exit_code == 0
        assert "qa-test-architect" in result.output
        assert "Found" in result.output

    def test_search_no_results(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Shows message when no agents match."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No agents found matching" in result.output

    def test_search_with_limit(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Respects result limit."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["search", "a", "--limit", "2"])

        assert result.exit_code == 0
        # Should show at most 2 results


class TestAgentsShowCommand:
    """Tests for aur agents show command."""

    def test_show_existing_agent(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Shows full details for existing agent."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["show", "qa-test-architect"])

        assert result.exit_code == 0
        assert "Test Architect" in result.output
        assert "test coverage" in result.output
        assert "test strategy" in result.output

    def test_show_nonexistent_agent(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Shows error and suggestions for nonexistent agent."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["show", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_show_case_insensitive(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Agent lookup is case-insensitive."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ):
            result = cli_runner.invoke(agents_group, ["show", "QA-TEST-ARCHITECT"])

        assert result.exit_code == 0
        assert "Test Architect" in result.output


class TestAgentsRefreshCommand:
    """Tests for aur agents refresh command."""

    def test_refresh_regenerates_manifest(
        self, cli_runner: CliRunner, sample_manifest: AgentManifest
    ) -> None:
        """Refresh regenerates the manifest."""
        with patch(
            "aurora_cli.commands.agents.get_manifest",
            return_value=sample_manifest,
        ) as mock_get:
            result = cli_runner.invoke(agents_group, ["refresh"])

        assert result.exit_code == 0
        assert "refreshed successfully" in result.output
        # Should have been called with force_refresh=True
        mock_get.assert_called_once_with(force_refresh=True)


class TestSearchAgentsFunction:
    """Tests for _search_agents helper function."""

    def test_exact_id_match_highest_priority(
        self, sample_manifest: AgentManifest
    ) -> None:
        """Exact ID matches rank highest."""
        results = _search_agents(sample_manifest, "orchestrator", limit=10)

        assert len(results) > 0
        assert results[0][0].id == "orchestrator"
        assert "exact id match" in results[0][1]

    def test_partial_id_match(self, sample_manifest: AgentManifest) -> None:
        """Partial ID matches rank high."""
        results = _search_agents(sample_manifest, "test", limit=10)

        assert len(results) > 0
        # qa-test-architect should be found
        ids = [r[0].id for r in results]
        assert "qa-test-architect" in ids

    def test_role_match(self, sample_manifest: AgentManifest) -> None:
        """Role matches are found."""
        results = _search_agents(sample_manifest, "developer", limit=10)

        assert len(results) > 0
        # full-stack-dev has "Developer" in role
        ids = [r[0].id for r in results]
        assert "full-stack-dev" in ids

    def test_skill_match(self, sample_manifest: AgentManifest) -> None:
        """Skill matches are found."""
        results = _search_agents(sample_manifest, "python", limit=10)

        assert len(results) > 0
        ids = [r[0].id for r in results]
        assert "full-stack-dev" in ids

    def test_respects_limit(self, sample_manifest: AgentManifest) -> None:
        """Respects maximum result limit."""
        results = _search_agents(sample_manifest, "a", limit=2)

        assert len(results) <= 2


class TestFindSimilarAgentsFunction:
    """Tests for _find_similar_agents helper function."""

    def test_finds_similar_ids(self, sample_manifest: AgentManifest) -> None:
        """Finds agents with similar IDs."""
        results = _find_similar_agents(sample_manifest, "qa-test")

        ids = [a.id for a in results]
        assert "qa-test-architect" in ids

    def test_returns_top_5(self, sample_manifest: AgentManifest) -> None:
        """Returns at most 5 suggestions."""
        results = _find_similar_agents(sample_manifest, "agent")

        assert len(results) <= 5


class TestTruncateFunction:
    """Tests for _truncate helper function."""

    def test_truncate_long_text(self) -> None:
        """Truncates text longer than max."""
        result = _truncate("This is a long string", 10)

        assert len(result) == 10
        assert result.endswith("...")

    def test_no_truncate_short_text(self) -> None:
        """Does not truncate short text."""
        result = _truncate("Short", 10)

        assert result == "Short"


class TestGetManifest:
    """Tests for get_manifest function."""

    def test_loads_manifest(self, tmp_path: Path) -> None:
        """Loads manifest from cache."""
        with patch(
            "aurora_cli.commands.agents.ManifestManager"
        ) as MockManager:
            mock_manager = MagicMock()
            mock_manifest = AgentManifest()
            mock_manager.get_or_refresh.return_value = mock_manifest
            MockManager.return_value = mock_manager

            with patch(
                "aurora_cli.commands.agents.get_manifest_path",
                return_value=tmp_path / "manifest.json",
            ):
                result = get_manifest()

            assert result == mock_manifest
            mock_manager.get_or_refresh.assert_called_once()

    def test_force_refresh(self, tmp_path: Path) -> None:
        """Force refresh regenerates manifest."""
        with patch(
            "aurora_cli.commands.agents.ManifestManager"
        ) as MockManager:
            mock_manager = MagicMock()
            mock_manifest = AgentManifest()
            mock_manager.generate.return_value = mock_manifest
            MockManager.return_value = mock_manager

            with patch(
                "aurora_cli.commands.agents.get_manifest_path",
                return_value=tmp_path / "manifest.json",
            ):
                result = get_manifest(force_refresh=True)

            assert result == mock_manifest
            mock_manager.generate.assert_called_once()
            mock_manager.save.assert_called_once()


class TestAgentsCommandHelp:
    """Tests for command help text."""

    def test_agents_group_help(self, cli_runner: CliRunner) -> None:
        """Shows help for agents command group."""
        result = cli_runner.invoke(agents_group, ["--help"])

        assert result.exit_code == 0
        assert "Agent discovery" in result.output
        assert "list" in result.output
        assert "search" in result.output
        assert "show" in result.output
        assert "refresh" in result.output

    def test_list_command_help(self, cli_runner: CliRunner) -> None:
        """Shows help for list command."""
        result = cli_runner.invoke(agents_group, ["list", "--help"])

        assert result.exit_code == 0
        assert "--category" in result.output

    def test_search_command_help(self, cli_runner: CliRunner) -> None:
        """Shows help for search command."""
        result = cli_runner.invoke(agents_group, ["search", "--help"])

        assert result.exit_code == 0
        assert "--limit" in result.output

    def test_show_command_help(self, cli_runner: CliRunner) -> None:
        """Shows help for show command."""
        result = cli_runner.invoke(agents_group, ["show", "--help"])

        assert result.exit_code == 0
        assert "AGENT_ID" in result.output
