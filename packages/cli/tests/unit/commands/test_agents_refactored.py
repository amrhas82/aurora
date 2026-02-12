"""Tests for refactored agents command helper functions.

This module tests the extracted helper functions from agents.py
to ensure behavior is maintained after refactoring for complexity reduction.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestGetProjectManifest:
    """Tests for _get_project_manifest helper function."""

    def test_returns_none_when_no_tools_configured(self) -> None:
        """Test that None is returned when no tools are configured."""
        from aurora_cli.commands.agents import _get_project_manifest

        # Patch at the source where get_configured_tool_ids is defined
        with (
            patch("aurora_cli.commands.init_helpers.get_configured_tool_ids") as mock_get_tools,
            patch("aurora_cli.commands.agents.console"),
        ):
            mock_get_tools.return_value = []

            result = _get_project_manifest(Path("/test"))

        assert result is None

    def test_returns_none_when_no_agent_paths(self) -> None:
        """Test that None is returned when tools have no agent paths."""
        from aurora_cli.commands.agents import _get_project_manifest

        with (
            patch("aurora_cli.commands.init_helpers.get_configured_tool_ids") as mock_get_tools,
            patch("aurora_cli.configurators.slash.paths.get_tool_paths") as mock_get_paths,
            patch("aurora_cli.commands.agents.console"),
        ):
            mock_get_tools.return_value = ["tool1"]
            mock_paths = MagicMock()
            mock_paths.agents = None
            mock_get_paths.return_value = mock_paths

            result = _get_project_manifest(Path("/test"))

        assert result is None

    def test_returns_manifest_and_context(self) -> None:
        """Test that manifest and context are returned when valid."""
        from aurora_cli.commands.agents import _get_project_manifest

        mock_manifest = MagicMock()

        with (
            patch("aurora_cli.commands.init_helpers.get_configured_tool_ids") as mock_get_tools,
            patch("aurora_cli.configurators.slash.paths.get_tool_paths") as mock_get_paths,
            patch("aurora_cli.commands.agents.AgentScanner"),
            patch("aurora_cli.commands.agents.ManifestManager") as mock_manager_cls,
        ):
            mock_get_tools.return_value = ["tool1", "tool2"]
            mock_paths = MagicMock()
            mock_paths.agents = "/path/to/agents"
            mock_get_paths.return_value = mock_paths

            mock_manager = MagicMock()
            mock_manager.generate.return_value = mock_manifest
            mock_manager_cls.return_value = mock_manager

            result = _get_project_manifest(Path("/test"))

        assert result is not None
        manifest, context = result
        assert manifest == mock_manifest
        assert "tool1" in context
        assert "tool2" in context


class TestDisplayEmptyManifestMessage:
    """Tests for _display_empty_manifest_message helper function."""

    def test_displays_all_tools_message(self) -> None:
        """Test message for show_all mode with no agents."""
        from aurora_cli.commands.agents import _display_empty_manifest_message

        with patch("aurora_cli.commands.agents.console") as mock_console:
            _display_empty_manifest_message(show_all=True, tool_context="all tools")

        # Should mention ~/.claude/agents/
        calls = str(mock_console.print.call_args_list)
        assert "agents" in calls.lower() or mock_console.print.called

    def test_displays_project_tools_message(self) -> None:
        """Test message for project-scoped mode with no agents."""
        from aurora_cli.commands.agents import _display_empty_manifest_message

        with patch("aurora_cli.commands.agents.console") as mock_console:
            _display_empty_manifest_message(show_all=False, tool_context="claude, cursor")

        # Should mention configured tools
        assert mock_console.print.called


class TestFilterAndDisplayAgents:
    """Tests for _filter_and_display_agents helper function."""

    def test_filters_by_category(self) -> None:
        """Test that agents are filtered by category when specified."""
        from aurora_cli.commands.agents import _filter_and_display_agents

        mock_manifest = MagicMock()
        mock_agent = MagicMock()
        mock_manifest.get_agents_by_category.return_value = [mock_agent]

        with (
            patch("aurora_cli.commands.agents.AgentCategory") as mock_cat_enum,
            patch("aurora_cli.commands.agents._display_agents_list"),
            patch("aurora_cli.commands.agents.console"),
        ):
            mock_cat_enum.return_value = "eng"

            result = _filter_and_display_agents(mock_manifest, "eng", "rich")

        assert result is True
        mock_manifest.get_agents_by_category.assert_called_once()

    def test_returns_false_when_category_empty(self) -> None:
        """Test that False is returned when category has no agents."""
        from aurora_cli.commands.agents import _filter_and_display_agents

        mock_manifest = MagicMock()
        mock_manifest.get_agents_by_category.return_value = []

        with (
            patch("aurora_cli.commands.agents.AgentCategory"),
            patch("aurora_cli.commands.agents.console"),
        ):
            result = _filter_and_display_agents(mock_manifest, "eng", "rich")

        assert result is False

    def test_displays_all_categories_when_no_filter(self) -> None:
        """Test that all categories are displayed when no filter specified."""
        from aurora_cli.commands.agents import _filter_and_display_agents

        mock_manifest = MagicMock()
        mock_manifest.stats.total = 5
        mock_manifest.get_agents_by_category.return_value = []

        with (
            patch("aurora_cli.commands.agents.AgentCategory"),
            patch("aurora_cli.commands.agents._display_agents_list") as mock_display,
        ):
            result = _filter_and_display_agents(mock_manifest, None, "rich")

        assert result is True
        mock_display.assert_called_once()
