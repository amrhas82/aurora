"""Tests for unified init command - test_init_unified.py

This test module verifies the unified `aur init` command that combines
initialization and planning setup into a single 3-step flow.

Test-Driven Development (TDD):
- Tests are written FIRST (RED phase)
- Implementation comes SECOND (GREEN phase)
- Refactor THIRD (REFACTOR phase)
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from aurora_cli.commands.init import run_step_1_planning_setup


class TestStep1PlanningSetup:
    """Test Step 1: Planning Setup (Git + Directories)."""

    def test_run_step_1_detects_existing_git_repository(self, tmp_path):
        """run_step_1_planning_setup() should detect existing .git directory."""
        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("subprocess.run") as mock_subprocess:
            result = run_step_1_planning_setup(tmp_path)

            # Should NOT call git init since .git exists
            mock_subprocess.assert_not_called()

        # Should still create directories and project.md
        assert (tmp_path / ".aurora" / "plans" / "active").exists()
        assert (tmp_path / ".aurora" / "project.md").exists()

    def test_run_step_1_prompts_git_init_when_no_git(self, tmp_path):
        """run_step_1_planning_setup() should prompt for git init when .git missing."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=False):
            result = run_step_1_planning_setup(tmp_path)

            # Should detect no git and prompt user
            # User declined, so no git initialization

        # Should still create Aurora directories
        assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_run_step_1_runs_git_init_when_user_accepts(self, tmp_path):
        """run_step_1_planning_setup() should run git init when user accepts."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=True) as mock_prompt:
            with patch("subprocess.run") as mock_subprocess:
                result = run_step_1_planning_setup(tmp_path)

                # Should prompt for git init
                mock_prompt.assert_called_once()

                # Should call git init
                mock_subprocess.assert_called_once_with(
                    ["git", "init"],
                    cwd=tmp_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

        # Should create directories
        assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_run_step_1_skips_git_init_when_user_declines(self, tmp_path):
        """run_step_1_planning_setup() should skip git init when user declines."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=False) as mock_prompt:
            with patch("subprocess.run") as mock_subprocess:
                result = run_step_1_planning_setup(tmp_path)

                # Should prompt
                mock_prompt.assert_called_once()

                # Should NOT call git init
                mock_subprocess.assert_not_called()

    def test_run_step_1_creates_plans_active_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/plans/active directory."""
        # Mock git detection to skip prompts
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        active_dir = tmp_path / ".aurora" / "plans" / "active"
        assert active_dir.exists()
        assert active_dir.is_dir()

    def test_run_step_1_creates_plans_archive_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/plans/archive directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        archive_dir = tmp_path / ".aurora" / "plans" / "archive"
        assert archive_dir.exists()
        assert archive_dir.is_dir()

    def test_run_step_1_creates_logs_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/logs directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        logs_dir = tmp_path / ".aurora" / "logs"
        assert logs_dir.exists()
        assert logs_dir.is_dir()

    def test_run_step_1_creates_cache_directory(self, tmp_path):
        """run_step_1_planning_setup() should create .aurora/cache directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        run_step_1_planning_setup(tmp_path)

        cache_dir = tmp_path / ".aurora" / "cache"
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_run_step_1_creates_project_md_with_metadata(self, tmp_path):
        """run_step_1_planning_setup() should create project.md with auto-detected metadata."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create pyproject.toml for detection
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry]\nname = "test-project"\n', encoding="utf-8")

        run_step_1_planning_setup(tmp_path)

        project_md = tmp_path / ".aurora" / "project.md"
        assert project_md.exists()

        content = project_md.read_text()
        assert "# Project Overview" in content
        assert "## Tech Stack" in content

    def test_run_step_1_preserves_existing_project_md(self, tmp_path):
        """run_step_1_planning_setup() should NOT overwrite existing project.md."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create .aurora directory and project.md
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        project_md = aurora_dir / "project.md"
        custom_content = "# My Custom Project\n\nDo not overwrite this!"
        project_md.write_text(custom_content, encoding="utf-8")

        run_step_1_planning_setup(tmp_path)

        # Should preserve custom content
        final_content = project_md.read_text()
        assert final_content == custom_content

    def test_run_step_1_returns_true_when_git_initialized(self, tmp_path):
        """run_step_1_planning_setup() should return True when git was initialized."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=True):
            with patch("subprocess.run"):
                result = run_step_1_planning_setup(tmp_path)

                assert result is True

    def test_run_step_1_returns_false_when_git_declined(self, tmp_path):
        """run_step_1_planning_setup() should return False when git init declined."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=False):
            result = run_step_1_planning_setup(tmp_path)

            assert result is False

    def test_run_step_1_returns_true_when_git_already_exists(self, tmp_path):
        """run_step_1_planning_setup() should return True when .git already exists."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = run_step_1_planning_setup(tmp_path)

        assert result is True

    def test_run_step_1_handles_git_init_failure(self, tmp_path):
        """run_step_1_planning_setup() should handle git init subprocess errors."""
        with patch("aurora_cli.commands.init.prompt_git_init", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git init")):
                # Should not raise - should handle gracefully
                with patch("aurora_cli.commands.init.console") as mock_console:
                    result = run_step_1_planning_setup(tmp_path)

                    # Should print error message
                    assert any("failed" in str(call).lower() or "error" in str(call).lower()
                               for call in mock_console.print.call_args_list)

                    # Should still create directories
                    assert (tmp_path / ".aurora" / "plans" / "active").exists()

    def test_run_step_1_is_idempotent(self, tmp_path):
        """run_step_1_planning_setup() should be safe to run multiple times."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Run first time
        result1 = run_step_1_planning_setup(tmp_path)
        assert result1 is True

        # Create custom content in project.md
        project_md = tmp_path / ".aurora" / "project.md"
        original_content = project_md.read_text()
        project_md.write_text("# Custom content", encoding="utf-8")

        # Run second time
        result2 = run_step_1_planning_setup(tmp_path)
        assert result2 is True

        # Should preserve custom content
        final_content = project_md.read_text()
        assert final_content == "# Custom content"

    def test_run_step_1_shows_success_message(self, tmp_path):
        """run_step_1_planning_setup() should display success message to user."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("aurora_cli.commands.init.console") as mock_console:
            run_step_1_planning_setup(tmp_path)

            # Should print success message
            assert any("created" in str(call).lower() or "detected" in str(call).lower()
                       for call in mock_console.print.call_args_list)
