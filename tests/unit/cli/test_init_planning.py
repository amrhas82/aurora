"""Tests for init-planning command."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aurora_cli.commands.init_planning import (
    detect_existing_setup,
    detect_configured_tools,
    create_directory_structure,
)


class TestDetectExistingSetup:
    """Tests for detect_existing_setup function."""

    def test_detect_no_existing_setup(self, tmp_path: Path):
        """Test detection when no .aurora directory exists."""
        assert detect_existing_setup(tmp_path) is False

    def test_detect_existing_setup(self, tmp_path: Path):
        """Test detection when .aurora directory exists."""
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        assert detect_existing_setup(tmp_path) is True


class TestDetectConfiguredTools:
    """Tests for detect_configured_tools function."""

    def test_detect_no_configured_tools(self, tmp_path: Path):
        """Test detection when no tools are configured."""
        result = detect_configured_tools(tmp_path)
        assert isinstance(result, dict)
        assert all(not configured for configured in result.values())

    def test_detect_claude_configured(self, tmp_path: Path):
        """Test detection of configured Claude Code."""
        # Create CLAUDE.md with Aurora markers
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "<!-- AURORA:START -->\nSome content\n<!-- AURORA:END -->"
        )

        result = detect_configured_tools(tmp_path)
        assert result.get("claude-code") is True

    def test_detect_partial_markers(self, tmp_path: Path):
        """Test that partial markers don't count as configured."""
        # Create CLAUDE.md with only start marker
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("<!-- AURORA:START -->\nSome content")

        result = detect_configured_tools(tmp_path)
        assert result.get("claude-code") is False


class TestCreateDirectoryStructure:
    """Tests for create_directory_structure function."""

    def test_creates_all_directories(self, tmp_path: Path):
        """Test that all required directories are created."""
        create_directory_structure(tmp_path)

        assert (tmp_path / ".aurora").exists()
        assert (tmp_path / ".aurora" / "plans" / "active").exists()
        assert (tmp_path / ".aurora" / "plans" / "archive").exists()
        assert (tmp_path / ".aurora" / "config" / "tools").exists()

    def test_creates_project_md(self, tmp_path: Path):
        """Test that project.md template is created."""
        create_directory_structure(tmp_path)

        project_md = tmp_path / ".aurora" / "project.md"
        assert project_md.exists()

        content = project_md.read_text()
        assert "# Project Overview" in content
        assert "Tech Stack" in content
        assert "Conventions" in content

    def test_idempotent_operation(self, tmp_path: Path):
        """Test that running twice doesn't cause errors."""
        create_directory_structure(tmp_path)
        create_directory_structure(tmp_path)  # Should not raise

        # Verify directories still exist
        assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_preserves_existing_project_md(self, tmp_path: Path):
        """Test that existing project.md is not overwritten."""
        # Create .aurora directory first
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()

        # Create existing project.md
        project_md = aurora_dir / "project.md"
        original_content = "# My Custom Content\nDo not overwrite!"
        project_md.write_text(original_content)

        # Run create_directory_structure
        create_directory_structure(tmp_path)

        # Verify content is preserved
        assert project_md.read_text() == original_content


class TestInitPlanningCommand:
    """Tests for init_planning_command function."""

    @pytest.mark.asyncio
    async def test_non_interactive_with_tools(self, tmp_path: Path):
        """Test non-interactive mode with specific tools."""
        from click.testing import CliRunner
        from aurora_cli.commands.init_planning import init_planning_command

        runner = CliRunner()
        result = runner.invoke(
            init_planning_command,
            ["--tools", "claude-code", "--path", str(tmp_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Aurora planning initialized successfully" in result.output
        assert (tmp_path / ".aurora").exists()
        assert (tmp_path / "CLAUDE.md").exists()

    @pytest.mark.asyncio
    async def test_non_interactive_with_all_tools(self, tmp_path: Path):
        """Test non-interactive mode with all tools."""
        from click.testing import CliRunner
        from aurora_cli.commands.init_planning import init_planning_command

        runner = CliRunner()
        result = runner.invoke(
            init_planning_command,
            ["--tools", "all", "--path", str(tmp_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "OPENCODE.md").exists()
        assert (tmp_path / "AMPCODE.md").exists()
        assert (tmp_path / "DROID.md").exists()
        assert (tmp_path / "AGENTS.md").exists()

    @pytest.mark.asyncio
    async def test_non_interactive_with_none_tools(self, tmp_path: Path):
        """Test non-interactive mode with no tools."""
        from click.testing import CliRunner
        from aurora_cli.commands.init_planning import init_planning_command

        runner = CliRunner()
        result = runner.invoke(
            init_planning_command,
            ["--tools", "none", "--path", str(tmp_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (tmp_path / ".aurora").exists()
        # No tool config files should be created
        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / "OPENCODE.md").exists()

    @pytest.mark.asyncio
    async def test_extend_mode_detection(self, tmp_path: Path):
        """Test that extend mode is detected correctly."""
        from click.testing import CliRunner
        from aurora_cli.commands.init_planning import init_planning_command

        # Create .aurora directory first
        (tmp_path / ".aurora").mkdir()

        runner = CliRunner()
        result = runner.invoke(
            init_planning_command,
            ["--tools", "claude-code", "--path", str(tmp_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Extend Setup" in result.output or "updated" in result.output.lower()

    @pytest.mark.asyncio
    async def test_directory_structure_created(self, tmp_path: Path):
        """Test that directory structure is created correctly."""
        from click.testing import CliRunner
        from aurora_cli.commands.init_planning import init_planning_command

        runner = CliRunner()
        result = runner.invoke(
            init_planning_command,
            ["--tools", "none", "--path", str(tmp_path)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (tmp_path / ".aurora" / "plans" / "active").is_dir()
        assert (tmp_path / ".aurora" / "plans" / "archive").is_dir()
        assert (tmp_path / ".aurora" / "config" / "tools").is_dir()
        assert (tmp_path / ".aurora" / "project.md").is_file()
