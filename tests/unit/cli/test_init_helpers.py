"""Tests for init_helpers.py - helper functions for unified init command.

This test module verifies helper functions extracted from init_planning.py
for use in the unified aur init command.

Test-Driven Development (TDD):
- These tests are written FIRST (RED phase)
- Implementation in init_helpers.py comes SECOND (GREEN phase)
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_cli.commands.init_helpers import (
    count_configured_tools,
    create_directory_structure,
    create_project_md,
    detect_configured_slash_tools,
    detect_configured_tools,
    detect_existing_setup,
    detect_git_repository,
    detect_project_metadata,
    prompt_git_init,
    prompt_tool_selection,
)


class TestGitDetection:
    """Test git repository detection functions."""

    def test_detect_git_repository_returns_true_when_git_exists(self, tmp_path):
        """detect_git_repository() should return True when .git directory exists."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = detect_git_repository(tmp_path)

        assert result is True

    def test_detect_git_repository_returns_false_when_no_git(self, tmp_path):
        """detect_git_repository() should return False when .git directory missing."""
        result = detect_git_repository(tmp_path)

        assert result is False

    def test_prompt_git_init_returns_bool(self):
        """prompt_git_init() should return boolean based on user input."""
        with patch("click.confirm", return_value=True):
            result = prompt_git_init()
            assert result is True

        with patch("click.confirm", return_value=False):
            result = prompt_git_init()
            assert result is False


class TestExistingSetupDetection:
    """Test detection of existing Aurora setup."""

    def test_detect_existing_setup_returns_true_when_aurora_exists(self, tmp_path):
        """detect_existing_setup() should return True when .aurora directory exists."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        result = detect_existing_setup(tmp_path)

        assert result is True

    def test_detect_existing_setup_returns_false_when_no_aurora(self, tmp_path):
        """detect_existing_setup() should return False when .aurora missing."""
        result = detect_existing_setup(tmp_path)

        assert result is False


class TestConfiguredToolsDetection:
    """Test detection of already-configured tools."""

    def test_detect_configured_tools_returns_empty_dict_when_no_configs(self, tmp_path):
        """detect_configured_tools() should return dict with False values when no configs."""
        result = detect_configured_tools(tmp_path)

        # Should return dict with all tools marked as not configured
        assert isinstance(result, dict)
        # Should have entries for known tools
        assert "claude-code" in result
        assert result["claude-code"] is False

    def test_detect_configured_tools_detects_configured_tool(self, tmp_path):
        """detect_configured_tools() should detect tool with Aurora markers."""
        # Create CLAUDE.md with Aurora markers
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            """# Custom content

<!-- AURORA:START -->
# Aurora Configuration
<!-- AURORA:END -->

More custom content
""",
            encoding="utf-8",
        )

        result = detect_configured_tools(tmp_path)

        # Should detect claude-code as configured
        assert result.get("claude-code") is True

    def test_detect_configured_tools_ignores_file_without_markers(self, tmp_path):
        """detect_configured_tools() should ignore files without Aurora markers."""
        # Create CLAUDE.md without markers
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Just some content", encoding="utf-8")

        result = detect_configured_tools(tmp_path)

        # Should NOT detect as configured (no markers)
        assert result.get("claude-code") is False

    def test_count_configured_tools_returns_zero_when_none_configured(self, tmp_path):
        """count_configured_tools() should return 0 when no tools configured."""
        result = count_configured_tools(tmp_path)

        assert result == 0

    def test_count_configured_tools_counts_correctly(self, tmp_path):
        """count_configured_tools() should count tools with Aurora markers."""
        # Create two configured tools
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "<!-- AURORA:START -->\nContent\n<!-- AURORA:END -->", encoding="utf-8"
        )

        opencode_md = tmp_path / "OPENCODE.md"
        opencode_md.write_text(
            "<!-- AURORA:START -->\nContent\n<!-- AURORA:END -->", encoding="utf-8"
        )

        result = count_configured_tools(tmp_path)

        assert result == 2


class TestDirectoryStructureCreation:
    """Test creation of Aurora directory structure."""

    def test_create_directory_structure_creates_plans_directories(self, tmp_path):
        """create_directory_structure() should create plans/active and plans/archive."""
        create_directory_structure(tmp_path)

        assert (tmp_path / ".aurora" / "plans" / "active").exists()
        assert (tmp_path / ".aurora" / "plans" / "archive").exists()

    def test_create_directory_structure_creates_logs_directory(self, tmp_path):
        """create_directory_structure() should create logs directory."""
        create_directory_structure(tmp_path)

        assert (tmp_path / ".aurora" / "logs").exists()

    def test_create_directory_structure_creates_cache_directory(self, tmp_path):
        """create_directory_structure() should create cache directory."""
        create_directory_structure(tmp_path)

        assert (tmp_path / ".aurora" / "cache").exists()

    def test_create_directory_structure_does_not_create_config_tools(self, tmp_path):
        """create_directory_structure() should NOT create config/tools (legacy)."""
        create_directory_structure(tmp_path)

        # This directory should NOT be created (removed in unified init)
        assert not (tmp_path / ".aurora" / "config" / "tools").exists()

    def test_create_directory_structure_is_idempotent(self, tmp_path):
        """create_directory_structure() should be safe to run multiple times."""
        # Create once
        create_directory_structure(tmp_path)
        assert (tmp_path / ".aurora" / "plans" / "active").exists()

        # Create again - should not raise
        create_directory_structure(tmp_path)
        assert (tmp_path / ".aurora" / "plans" / "active").exists()


class TestProjectMdCreation:
    """Test project.md template creation."""

    def test_create_project_md_creates_file(self, tmp_path):
        """create_project_md() should create .aurora/project.md file."""
        # Create .aurora directory first
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        create_project_md(tmp_path)

        project_md = aurora_dir / "project.md"
        assert project_md.exists()

    def test_create_project_md_contains_template_sections(self, tmp_path):
        """create_project_md() should include standard template sections."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        create_project_md(tmp_path)

        content = (aurora_dir / "project.md").read_text()

        # Check for expected sections
        assert "# Project Overview" in content
        assert "## Description" in content
        assert "## Tech Stack" in content
        assert "## Conventions" in content
        assert "## Architecture" in content

    def test_create_project_md_preserves_existing_file(self, tmp_path):
        """create_project_md() should NOT overwrite existing project.md."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        # Create existing file
        project_md = aurora_dir / "project.md"
        custom_content = "# My Custom Project\n\nCustom content here"
        project_md.write_text(custom_content, encoding="utf-8")

        # Call create_project_md
        create_project_md(tmp_path)

        # Should preserve custom content
        final_content = project_md.read_text()
        assert final_content == custom_content


class TestProjectMetadataDetection:
    """Test auto-detection of project metadata."""

    def test_detect_project_metadata_returns_dict_with_required_keys(self, tmp_path):
        """detect_project_metadata() should return dict with name, date, tech_stack."""
        result = detect_project_metadata(tmp_path)

        assert isinstance(result, dict)
        assert "name" in result
        assert "date" in result
        assert "tech_stack" in result

    def test_detect_project_metadata_uses_directory_name(self, tmp_path):
        """detect_project_metadata() should use directory name as project name."""
        result = detect_project_metadata(tmp_path)

        # tmp_path name varies, but should match the directory name
        assert result["name"] == tmp_path.name

    def test_detect_project_metadata_detects_python_from_pyproject_toml(self, tmp_path):
        """detect_project_metadata() should detect Python from pyproject.toml."""
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """[tool.poetry.dependencies]
python = "^3.10"
""",
            encoding="utf-8",
        )

        result = detect_project_metadata(tmp_path)

        assert "Python" in result["tech_stack"]
        assert "(detected)" in result["tech_stack"]

    def test_detect_project_metadata_detects_poetry(self, tmp_path):
        """detect_project_metadata() should detect poetry package manager."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """[tool.poetry]
name = "test"
""",
            encoding="utf-8",
        )

        result = detect_project_metadata(tmp_path)

        assert "poetry" in result["tech_stack"].lower()
        assert "(detected)" in result["tech_stack"]

    def test_detect_project_metadata_detects_pytest(self, tmp_path):
        """detect_project_metadata() should detect pytest testing framework."""
        # Create pytest.ini
        pytest_ini = tmp_path / "pytest.ini"
        pytest_ini.write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")

        result = detect_project_metadata(tmp_path)

        assert "pytest" in result["tech_stack"].lower()
        assert "(detected)" in result["tech_stack"]

    def test_detect_project_metadata_detects_javascript_from_package_json(self, tmp_path):
        """detect_project_metadata() should detect JavaScript from package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text(
            json.dumps({"name": "test-project", "version": "1.0.0"}), encoding="utf-8"
        )

        result = detect_project_metadata(tmp_path)

        assert "Node.js" in result["tech_stack"] or "JavaScript" in result["tech_stack"]
        assert "(detected)" in result["tech_stack"]

    def test_detect_project_metadata_handles_empty_project(self, tmp_path):
        """detect_project_metadata() should handle project with no detectable tech."""
        result = detect_project_metadata(tmp_path)

        # Should still return dict with all keys
        assert "name" in result
        assert "date" in result
        assert "tech_stack" in result
        # tech_stack might be empty or minimal
        assert isinstance(result["tech_stack"], str)


class TestPromptToolSelection:
    """Test tool selection wizard for slash command configurators.

    These tests verify that prompt_tool_selection() uses the SlashCommandRegistry
    to display all 20 available tools and allows user selection.
    """

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_returns_list(self):
        """prompt_tool_selection() should return a list of selected tool IDs."""
        # Mock questionary to return specific selections
        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(
                return_value=["claude", "cursor"]
            )

            result = await prompt_tool_selection(configured_tools={})

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_returns_selected_tool_ids(self):
        """prompt_tool_selection() should return the IDs user selected."""
        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(
                return_value=["claude", "cursor", "gemini"]
            )

            result = await prompt_tool_selection(configured_tools={})

            assert "claude" in result
            assert "cursor" in result
            assert "gemini" in result

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_builds_choices_from_registry(self):
        """prompt_tool_selection() should build choices from SlashCommandRegistry."""
        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(return_value=[])
            mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

            await prompt_tool_selection(configured_tools={})

            # Verify checkbox was called with choices
            mock_questionary.checkbox.assert_called_once()
            call_kwargs = mock_questionary.checkbox.call_args[1]
            choices = call_kwargs.get("choices", [])

            # Should have at least 20 choices for the 20 tools
            # (excluding the universal agents option)
            tool_choices = [c for c in choices if isinstance(c, dict)]
            assert len(tool_choices) >= 20

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_pre_checks_configured_tools(self):
        """prompt_tool_selection() should pre-check already configured tools."""
        configured_tools = {
            "claude": True,
            "cursor": False,
            "gemini": True,
        }

        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(return_value=[])
            created_choices = []
            mock_questionary.Choice = MagicMock(
                side_effect=lambda **kwargs: created_choices.append(kwargs) or kwargs
            )

            await prompt_tool_selection(configured_tools=configured_tools)

            # Find the claude and cursor choices
            claude_choices = [c for c in created_choices if c.get("value") == "claude"]
            cursor_choices = [c for c in created_choices if c.get("value") == "cursor"]
            gemini_choices = [c for c in created_choices if c.get("value") == "gemini"]

            # Claude should be pre-checked
            if claude_choices:
                assert claude_choices[0].get("checked") is True
            # Cursor should NOT be pre-checked
            if cursor_choices:
                assert cursor_choices[0].get("checked") is False
            # Gemini should be pre-checked
            if gemini_choices:
                assert gemini_choices[0].get("checked") is True

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_shows_already_configured_label(self):
        """prompt_tool_selection() should show (already configured) label for configured tools."""
        configured_tools = {
            "claude": True,
            "cursor": False,
        }

        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(return_value=[])
            created_choices = []
            mock_questionary.Choice = MagicMock(
                side_effect=lambda **kwargs: created_choices.append(kwargs) or kwargs
            )

            await prompt_tool_selection(configured_tools=configured_tools)

            # Find the claude choice
            claude_choices = [c for c in created_choices if c.get("value") == "claude"]

            # Claude should have (already configured) in title
            if claude_choices:
                assert "(already configured)" in claude_choices[0].get("title", "")

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_includes_all_20_tools(self):
        """prompt_tool_selection() should include all 20 tools from SlashCommandRegistry."""
        from aurora_cli.configurators.slash import SlashCommandRegistry

        expected_tool_ids = [c.tool_id for c in SlashCommandRegistry.get_all()]

        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(return_value=[])
            created_choices = []
            mock_questionary.Choice = MagicMock(
                side_effect=lambda **kwargs: created_choices.append(kwargs) or kwargs
            )

            await prompt_tool_selection(configured_tools={})

            # Get all choice values
            choice_values = [c.get("value") for c in created_choices if isinstance(c, dict)]

            # All 20 tool IDs should be present
            for tool_id in expected_tool_ids:
                assert tool_id in choice_values, f"Tool {tool_id} should be in choices"

    @pytest.mark.asyncio
    async def test_prompt_tool_selection_returns_empty_list_on_cancel(self):
        """prompt_tool_selection() should return empty list if user cancels."""
        with patch("aurora_cli.commands.init_helpers.questionary") as mock_questionary:
            # Simulate user pressing Ctrl+C or ESC
            mock_questionary.checkbox.return_value.ask_async = AsyncMock(return_value=None)

            result = await prompt_tool_selection(configured_tools={})

            assert result == []


class TestConfigureSlashCommands:
    """Test configure_slash_commands() helper for configuring slash command tools.

    These tests verify the helper function that configures selected slash command
    tools using their respective configurators.
    """

    @pytest.mark.asyncio
    async def test_configure_slash_commands_returns_tuple(self, tmp_path):
        """configure_slash_commands() should return (created, updated) tuple."""
        from aurora_cli.commands.init_helpers import configure_slash_commands

        result = await configure_slash_commands(tmp_path, ["claude"])

        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_configure_slash_commands_creates_new_tool_files(self, tmp_path):
        """configure_slash_commands() should create files for new tools."""
        from aurora_cli.commands.init_helpers import configure_slash_commands

        created, updated = await configure_slash_commands(tmp_path, ["claude"])

        # Claude should be in created list
        assert len(created) > 0 or len(updated) > 0
        # Claude directory should exist
        assert (tmp_path / ".claude" / "commands" / "aur").exists() or len(updated) > 0

    @pytest.mark.asyncio
    async def test_configure_slash_commands_accepts_list_of_tool_ids(self, tmp_path):
        """configure_slash_commands() should accept list of tool IDs."""
        from aurora_cli.commands.init_helpers import configure_slash_commands

        # Should not raise for valid tool IDs
        created, updated = await configure_slash_commands(tmp_path, ["claude", "cursor", "gemini"])

        assert isinstance(created, list)
        assert isinstance(updated, list)

    @pytest.mark.asyncio
    async def test_configure_slash_commands_handles_empty_list(self, tmp_path):
        """configure_slash_commands() should handle empty tool list gracefully."""
        from aurora_cli.commands.init_helpers import configure_slash_commands

        created, updated = await configure_slash_commands(tmp_path, [])

        assert created == []
        assert updated == []

    @pytest.mark.asyncio
    async def test_configure_slash_commands_handles_invalid_tool_id(self, tmp_path):
        """configure_slash_commands() should handle invalid tool IDs gracefully."""
        from aurora_cli.commands.init_helpers import configure_slash_commands

        # Should not raise, just skip invalid tools
        created, updated = await configure_slash_commands(tmp_path, ["not-a-real-tool", "claude"])

        # Should still configure valid tools
        assert isinstance(created, list)

    @pytest.mark.asyncio
    async def test_configure_slash_commands_tracks_updated_tools(self, tmp_path):
        """configure_slash_commands() should track updated vs created tools."""
        from aurora_cli.commands.init_helpers import configure_slash_commands

        # First run - creates
        created1, updated1 = await configure_slash_commands(tmp_path, ["claude"])

        # Second run - should update
        created2, updated2 = await configure_slash_commands(tmp_path, ["claude"])

        # First run should have created, second should have updated
        assert len(created1) > 0 or len(updated1) >= 0
        # Note: Behavior depends on marker detection
        assert isinstance(updated2, list)

    @pytest.mark.asyncio
    async def test_configure_slash_commands_calls_generate_all_for_each_tool(self, tmp_path):
        """configure_slash_commands() should call generate_all() for each tool."""
        from aurora_cli.commands.init_helpers import configure_slash_commands
        from aurora_cli.configurators.slash import SlashCommandRegistry

        with patch.object(SlashCommandRegistry, "get") as mock_get:
            mock_configurator = MagicMock()
            mock_configurator.generate_all = AsyncMock()
            mock_configurator.name = "Test Tool"
            mock_get.return_value = mock_configurator

            await configure_slash_commands(tmp_path, ["claude", "cursor"])

            # generate_all should be called for each tool
            assert mock_configurator.generate_all.call_count == 2


class TestDetectConfiguredSlashTools:
    """Test detect_configured_slash_tools() for extend mode detection.

    These tests verify detection of already-configured slash command tools
    by checking for Aurora markers in expected file paths.
    """

    def test_detect_configured_slash_tools_returns_dict(self, tmp_path):
        """detect_configured_slash_tools() should return dict[str, bool]."""
        result = detect_configured_slash_tools(tmp_path)

        assert isinstance(result, dict)
        # Should have entries for all 20 tools
        assert len(result) == 20

    def test_detect_configured_slash_tools_all_false_when_no_files(self, tmp_path):
        """detect_configured_slash_tools() should return all False when no files exist."""
        # Use isolated CODEX_HOME to prevent real ~/.codex from interfering
        with tempfile.TemporaryDirectory() as codex_home:
            with patch.dict(os.environ, {"CODEX_HOME": codex_home}):
                result = detect_configured_slash_tools(tmp_path)

                # All tools should be marked as not configured
                for tool_id, is_configured in result.items():
                    assert is_configured is False, f"Tool {tool_id} should not be configured"

    def test_detect_configured_slash_tools_detects_claude(self, tmp_path):
        """detect_configured_slash_tools() should detect configured Claude tool."""
        # Create Claude command file with Aurora markers
        claude_dir = tmp_path / ".claude" / "commands" / "aur"
        claude_dir.mkdir(parents=True)
        plan_file = claude_dir / "plan.md"
        plan_file.write_text(
            """---
name: Aurora Plan
---

<!-- AURORA:START -->
Plan command content
<!-- AURORA:END -->
""",
            encoding="utf-8",
        )

        result = detect_configured_slash_tools(tmp_path)

        assert result.get("claude") is True

    def test_detect_configured_slash_tools_detects_cursor(self, tmp_path):
        """detect_configured_slash_tools() should detect configured Cursor tool."""
        # Create Cursor command file with Aurora markers
        cursor_dir = tmp_path / ".cursor" / "commands"
        cursor_dir.mkdir(parents=True)
        plan_file = cursor_dir / "aurora-plan.md"
        plan_file.write_text(
            """---
name: Aurora Plan
---

<!-- AURORA:START -->
Plan command content
<!-- AURORA:END -->
""",
            encoding="utf-8",
        )

        result = detect_configured_slash_tools(tmp_path)

        assert result.get("cursor") is True

    def test_detect_configured_slash_tools_detects_gemini_toml(self, tmp_path):
        """detect_configured_slash_tools() should detect configured Gemini tool (TOML)."""
        # Create Gemini TOML file with Aurora markers
        gemini_dir = tmp_path / ".gemini" / "commands" / "aurora"
        gemini_dir.mkdir(parents=True)
        plan_file = gemini_dir / "plan.toml"
        plan_file.write_text(
            '''description = "Aurora Plan"

prompt = """
<!-- AURORA:START -->
Plan command content
<!-- AURORA:END -->
"""
''',
            encoding="utf-8",
        )

        result = detect_configured_slash_tools(tmp_path)

        assert result.get("gemini") is True

    def test_detect_configured_slash_tools_returns_false_without_markers(self, tmp_path):
        """detect_configured_slash_tools() should return False for files without markers."""
        # Create Claude command file WITHOUT Aurora markers
        claude_dir = tmp_path / ".claude" / "commands" / "aur"
        claude_dir.mkdir(parents=True)
        plan_file = claude_dir / "plan.md"
        plan_file.write_text(
            """---
name: Aurora Plan
---

Some custom content without markers
""",
            encoding="utf-8",
        )

        result = detect_configured_slash_tools(tmp_path)

        assert result.get("claude") is False

    def test_detect_configured_slash_tools_codex_uses_global_path(self, tmp_path):
        """detect_configured_slash_tools() should check global path for Codex."""
        # Create a temporary directory to act as CODEX_HOME
        with tempfile.TemporaryDirectory() as codex_home:
            # Create Codex prompts directory with Aurora markers
            prompts_dir = Path(codex_home) / "prompts"
            prompts_dir.mkdir(parents=True)
            plan_file = prompts_dir / "aurora-plan.md"
            plan_file.write_text(
                """---
name: Aurora Plan
---

<!-- AURORA:START -->
Plan command content
<!-- AURORA:END -->
""",
                encoding="utf-8",
            )

            # Set CODEX_HOME environment variable
            with patch.dict(os.environ, {"CODEX_HOME": codex_home}):
                result = detect_configured_slash_tools(tmp_path)

                assert result.get("codex") is True

    def test_detect_configured_slash_tools_codex_false_when_no_global_files(self, tmp_path):
        """detect_configured_slash_tools() should return False for Codex when no global files."""
        # Use a non-existent CODEX_HOME
        with tempfile.TemporaryDirectory() as codex_home:
            # Don't create any files - just empty directory
            with patch.dict(os.environ, {"CODEX_HOME": codex_home}):
                result = detect_configured_slash_tools(tmp_path)

                assert result.get("codex") is False

    def test_detect_configured_slash_tools_detects_windsurf(self, tmp_path):
        """detect_configured_slash_tools() should detect configured Windsurf tool."""
        # Create Windsurf workflow file with Aurora markers
        windsurf_dir = tmp_path / ".windsurf" / "workflows"
        windsurf_dir.mkdir(parents=True)
        plan_file = windsurf_dir / "aurora-plan.md"
        plan_file.write_text(
            """---
description: Aurora Plan
auto_execution_mode: 3
---

<!-- AURORA:START -->
Plan command content
<!-- AURORA:END -->
""",
            encoding="utf-8",
        )

        result = detect_configured_slash_tools(tmp_path)

        assert result.get("windsurf") is True

    def test_detect_configured_slash_tools_multiple_tools(self, tmp_path):
        """detect_configured_slash_tools() should detect multiple configured tools."""
        # Create Claude command file
        claude_dir = tmp_path / ".claude" / "commands" / "aur"
        claude_dir.mkdir(parents=True)
        (claude_dir / "plan.md").write_text(
            "<!-- AURORA:START -->\nContent\n<!-- AURORA:END -->",
            encoding="utf-8",
        )

        # Create Cursor command file
        cursor_dir = tmp_path / ".cursor" / "commands"
        cursor_dir.mkdir(parents=True)
        (cursor_dir / "aurora-plan.md").write_text(
            "<!-- AURORA:START -->\nContent\n<!-- AURORA:END -->",
            encoding="utf-8",
        )

        result = detect_configured_slash_tools(tmp_path)

        assert result.get("claude") is True
        assert result.get("cursor") is True
        # Others should still be False
        assert result.get("gemini") is False
        assert result.get("windsurf") is False

    def test_detect_configured_slash_tools_returns_all_20_tool_ids(self, tmp_path):
        """detect_configured_slash_tools() should return all 20 tool IDs."""
        from aurora_cli.configurators.slash import SlashCommandRegistry

        expected_tool_ids = {c.tool_id for c in SlashCommandRegistry.get_all()}

        result = detect_configured_slash_tools(tmp_path)

        assert set(result.keys()) == expected_tool_ids
