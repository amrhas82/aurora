"""Tests for CursorSlashCommandConfigurator.

Tests the Cursor slash command configurator that creates commands
in .cursor/commands/ directory with aurora-{command}.md naming.
"""

from pathlib import Path

import pytest

from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.cursor import CursorSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


class TestCursorSlashCommandConfiguratorProperties:
    """Tests for basic properties of CursorSlashCommandConfigurator."""

    def test_tool_id_returns_cursor(self):
        """Test that tool_id property returns 'cursor'."""
        config = CursorSlashCommandConfigurator()
        assert config.tool_id == "cursor"

    def test_is_available_returns_true(self):
        """Test that is_available property returns True.

        Cursor is always available (doesn't require detection).
        """
        config = CursorSlashCommandConfigurator()
        assert config.is_available is True

    def test_inherits_from_slash_command_configurator(self):
        """Test that CursorSlashCommandConfigurator inherits from SlashCommandConfigurator."""
        assert issubclass(CursorSlashCommandConfigurator, SlashCommandConfigurator)

    def test_can_instantiate(self):
        """Test that CursorSlashCommandConfigurator can be instantiated."""
        config = CursorSlashCommandConfigurator()
        assert config is not None


class TestCursorSlashCommandConfiguratorPaths:
    """Tests for path-related methods."""

    def test_get_relative_path_plan(self):
        """Test get_relative_path returns correct path for 'plan' command."""
        config = CursorSlashCommandConfigurator()
        path = config.get_relative_path("plan")
        assert path == ".cursor/commands/aurora-plan.md"

    def test_get_relative_path_all_commands(self):
        """Test get_relative_path works for all standard commands."""
        config = CursorSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(".cursor/commands/")
            assert path.endswith(".md")
            assert f"aurora-{cmd_id}" in path

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Test resolve_absolute_path returns absolute path."""
        config = CursorSlashCommandConfigurator()
        abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()
        expected = str(tmp_path / ".cursor/commands/aurora-plan.md")
        assert abs_path == expected


class TestCursorSlashCommandConfiguratorFrontmatter:
    """Tests for frontmatter generation."""

    def test_get_frontmatter_plan_returns_yaml(self):
        """Test get_frontmatter returns YAML frontmatter for 'plan' command."""
        config = CursorSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert frontmatter is not None
        assert frontmatter.startswith("---")
        assert frontmatter.endswith("---")

    def test_get_frontmatter_plan_has_name(self):
        """Test frontmatter contains 'name' field with /aurora-{command} pattern."""
        config = CursorSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "name:" in frontmatter
        assert "/aurora-plan" in frontmatter

    def test_get_frontmatter_plan_has_id(self):
        """Test frontmatter contains 'id' field."""
        config = CursorSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "id:" in frontmatter
        assert "aurora-plan" in frontmatter

    def test_get_frontmatter_plan_has_category(self):
        """Test frontmatter contains 'category' field."""
        config = CursorSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "category:" in frontmatter
        assert "Aurora" in frontmatter

    def test_get_frontmatter_plan_has_description(self):
        """Test frontmatter contains 'description' field."""
        config = CursorSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "description:" in frontmatter

    def test_get_frontmatter_all_commands(self):
        """Test get_frontmatter works for all standard commands."""
        config = CursorSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            assert frontmatter is not None, f"Frontmatter for {cmd_id} should not be None"
            assert "---" in frontmatter, f"Frontmatter for {cmd_id} should have YAML delimiters"
            assert "name:" in frontmatter, f"Frontmatter for {cmd_id} should have name"
            assert "id:" in frontmatter, f"Frontmatter for {cmd_id} should have id"
            assert (
                "description:" in frontmatter
            ), f"Frontmatter for {cmd_id} should have description"

    def test_frontmatter_includes_aurora_naming_pattern(self):
        """Test frontmatter uses /aurora-{command} naming pattern."""
        config = CursorSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            # The name field should include the /aurora-{command} pattern
            assert (
                f"/aurora-{cmd_id}" in frontmatter
            ), f"Frontmatter for {cmd_id} should include /aurora-{cmd_id} naming pattern"


class TestCursorSlashCommandConfiguratorBody:
    """Tests for body content generation."""

    def test_get_body_plan_returns_template(self):
        """Test get_body returns content from slash_commands templates."""
        config = CursorSlashCommandConfigurator()
        body = config.get_body("plan")

        # Should return the same content as get_command_body
        expected = get_command_body("plan")
        assert body == expected

    def test_get_body_all_commands(self):
        """Test get_body works for all standard commands."""
        config = CursorSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            body = config.get_body(cmd_id)
            expected = get_command_body(cmd_id)
            assert body == expected, f"Body for {cmd_id} should match template"


class TestCursorSlashCommandConfiguratorGenerateAll:
    """Tests for generate_all method."""

    def test_generate_all_creates_6_files(self, tmp_path: Path):
        """Test generate_all creates 6 command files (one for each command)."""
        config = CursorSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)
        assert len(created) == 6

    def test_generate_all_creates_files_in_cursor_directory(self, tmp_path: Path):
        """Test generate_all creates files in .cursor/commands/ directory."""
        config = CursorSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        commands_dir = tmp_path / ".cursor" / "commands"
        assert commands_dir.exists()
        assert commands_dir.is_dir()

    def test_generate_all_creates_plan_file(self, tmp_path: Path):
        """Test generate_all creates aurora-plan.md file."""
        config = CursorSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".cursor" / "commands" / "aurora-plan.md"
        assert plan_file.exists()

    def test_generate_all_file_has_frontmatter(self, tmp_path: Path):
        """Test generated file starts with YAML frontmatter."""
        config = CursorSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".cursor" / "commands" / "aurora-plan.md"
        content = plan_file.read_text()

        assert content.startswith("---")

    def test_generate_all_file_has_aurora_markers(self, tmp_path: Path):
        """Test generated file contains Aurora markers."""
        config = CursorSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".cursor" / "commands" / "aurora-plan.md"
        content = plan_file.read_text()

        assert AURORA_MARKERS["start"] in content
        assert AURORA_MARKERS["end"] in content

    def test_generate_all_creates_all_command_files(self, tmp_path: Path):
        """Test generate_all creates all 7 command files with correct names."""
        config = CursorSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        commands_dir = tmp_path / ".cursor" / "commands"
        for cmd_id in ALL_COMMANDS:
            filepath = commands_dir / f"aurora-{cmd_id}.md"
            assert filepath.exists(), f"Expected file aurora-{cmd_id}.md to exist"

    def test_generate_all_returns_relative_paths(self, tmp_path: Path):
        """Test generate_all returns relative paths."""
        config = CursorSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        for path in created:
            assert not Path(path).is_absolute()
            assert path.startswith(".cursor/commands/")


class TestCursorSlashCommandConfiguratorUpdateExisting:
    """Tests for update_existing method."""

    def test_update_existing_preserves_custom_content(self, tmp_path: Path):
        """Test update_existing preserves custom content outside Aurora markers."""
        config = CursorSlashCommandConfigurator()

        # First generate the file
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".cursor" / "commands" / "aurora-plan.md"
        original_content = plan_file.read_text()

        # Add custom content outside markers
        frontmatter_end = original_content.find("---", 4) + 3

        custom_line = "\n\n<!-- Custom Cursor-specific note -->\n"
        modified_content = (
            original_content[:frontmatter_end] + custom_line + original_content[frontmatter_end:]
        )
        plan_file.write_text(modified_content)

        # Now update existing
        config.update_existing(str(tmp_path), ".aurora")

        # Custom content should still be there
        updated_content = plan_file.read_text()
        assert "Custom Cursor-specific note" in updated_content

    def test_update_existing_only_updates_existing_files(self, tmp_path: Path):
        """Test update_existing does not create new files."""
        config = CursorSlashCommandConfigurator()

        # Create only one file
        commands_dir = tmp_path / ".cursor" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)
        plan_file = commands_dir / "aurora-plan.md"

        frontmatter = config.get_frontmatter("plan")
        plan_file.write_text(
            f"{frontmatter}\n" f"{AURORA_MARKERS['start']}\n" f"Body\n" f"{AURORA_MARKERS['end']}\n"
        )

        # Update existing
        updated = config.update_existing(str(tmp_path), ".aurora")

        # Only the one file should be updated
        assert len(updated) == 1

        # Other files should NOT have been created
        query_file = commands_dir / "aurora-query.md"
        assert not query_file.exists()


class TestCursorSlashCommandConfiguratorTargets:
    """Tests for get_targets method."""

    def test_get_targets_returns_6_targets(self):
        """Test get_targets returns 6 targets (one per command)."""
        config = CursorSlashCommandConfigurator()
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)
        assert len(targets) == 6

    def test_get_targets_returns_slash_command_targets(self):
        """Test get_targets returns SlashCommandTarget objects."""
        config = CursorSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    def test_get_targets_has_all_command_ids(self):
        """Test get_targets includes all command IDs."""
        config = CursorSlashCommandConfigurator()
        targets = config.get_targets()

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)

    def test_get_targets_paths_match_get_relative_path(self):
        """Test that target paths match get_relative_path output."""
        config = CursorSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            expected_path = config.get_relative_path(target.command_id)
            assert target.path == expected_path
