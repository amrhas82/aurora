"""Tests for init_helpers.py - helper functions for unified init command.

This test module verifies helper functions extracted from init_planning.py
for use in the unified aur init command.

Test-Driven Development (TDD):
- These tests are written FIRST (RED phase)
- Implementation in init_helpers.py comes SECOND (GREEN phase)
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.commands.init_helpers import (
    count_configured_tools,
    create_directory_structure,
    create_project_md,
    detect_configured_tools,
    detect_existing_setup,
    detect_git_repository,
    detect_project_metadata,
    prompt_git_init,
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
        claude_md.write_text("<!-- AURORA:START -->\nContent\n<!-- AURORA:END -->", encoding="utf-8")

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
