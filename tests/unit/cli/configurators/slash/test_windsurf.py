"""Tests for WindsurfSlashCommandConfigurator.

Tests the Windsurf slash command configurator that creates commands
in .windsurf/workflows/ directory with aurora-{command}.md naming
and special auto_execution_mode: 3 frontmatter.
"""

from pathlib import Path

from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.windsurf import WindsurfSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


class TestWindsurfSlashCommandConfiguratorProperties:
    """Tests for basic properties of WindsurfSlashCommandConfigurator."""

    def test_tool_id_returns_windsurf(self):
        """Test that tool_id property returns 'windsurf'."""
        config = WindsurfSlashCommandConfigurator()
        assert config.tool_id == "windsurf"

    def test_is_available_returns_true(self):
        """Test that is_available property returns True.

        Windsurf is always available (doesn't require detection).
        """
        config = WindsurfSlashCommandConfigurator()
        assert config.is_available is True

    def test_inherits_from_slash_command_configurator(self):
        """Test that WindsurfSlashCommandConfigurator inherits from SlashCommandConfigurator."""
        assert issubclass(WindsurfSlashCommandConfigurator, SlashCommandConfigurator)

    def test_can_instantiate(self):
        """Test that WindsurfSlashCommandConfigurator can be instantiated."""
        config = WindsurfSlashCommandConfigurator()
        assert config is not None


class TestWindsurfSlashCommandConfiguratorPaths:
    """Tests for path-related methods."""

    def test_get_relative_path_plan(self):
        """Test get_relative_path returns correct path for 'plan' command."""
        config = WindsurfSlashCommandConfigurator()
        path = config.get_relative_path("plan")
        assert path == ".windsurf/workflows/aurora-plan.md"

    def test_get_relative_path_all_commands(self):
        """Test get_relative_path works for all standard commands."""
        config = WindsurfSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(".windsurf/workflows/")
            assert path.endswith(".md")
            assert f"aurora-{cmd_id}" in path

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Test resolve_absolute_path returns absolute path."""
        config = WindsurfSlashCommandConfigurator()
        abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()
        expected = str(tmp_path / ".windsurf/workflows/aurora-plan.md")
        assert abs_path == expected


class TestWindsurfSlashCommandConfiguratorFrontmatter:
    """Tests for frontmatter generation with auto_execution_mode."""

    def test_get_frontmatter_plan_returns_yaml(self):
        """Test get_frontmatter returns YAML frontmatter for 'plan' command."""
        config = WindsurfSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert frontmatter is not None
        assert frontmatter.startswith("---")
        assert frontmatter.endswith("---")

    def test_get_frontmatter_plan_has_description(self):
        """Test frontmatter contains 'description' field."""
        config = WindsurfSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "description:" in frontmatter

    def test_get_frontmatter_plan_has_auto_execution_mode(self):
        """Test frontmatter contains 'auto_execution_mode: 3' field.

        Windsurf uses auto_execution_mode: 3 for workflows.
        """
        config = WindsurfSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "auto_execution_mode:" in frontmatter
        assert "auto_execution_mode: 3" in frontmatter

    def test_get_frontmatter_all_commands_have_auto_execution_mode(self):
        """Test all commands have auto_execution_mode: 3 in frontmatter."""
        config = WindsurfSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            assert frontmatter is not None
            assert (
                "auto_execution_mode: 3" in frontmatter
            ), f"Frontmatter for {cmd_id} should have auto_execution_mode: 3"

    def test_get_frontmatter_all_commands(self):
        """Test get_frontmatter works for all standard commands."""
        config = WindsurfSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            assert frontmatter is not None, f"Frontmatter for {cmd_id} should not be None"
            assert "---" in frontmatter, f"Frontmatter for {cmd_id} should have YAML delimiters"
            assert (
                "description:" in frontmatter
            ), f"Frontmatter for {cmd_id} should have description"


class TestWindsurfSlashCommandConfiguratorBody:
    """Tests for body content generation."""

    def test_get_body_plan_returns_template(self):
        """Test get_body returns content from slash_commands templates."""
        config = WindsurfSlashCommandConfigurator()
        body = config.get_body("plan")

        expected = get_command_body("plan")
        assert body == expected

    def test_get_body_all_commands(self):
        """Test get_body works for all standard commands."""
        config = WindsurfSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            body = config.get_body(cmd_id)
            expected = get_command_body(cmd_id)
            assert body == expected, f"Body for {cmd_id} should match template"


class TestWindsurfSlashCommandConfiguratorGenerateAll:
    """Tests for generate_all method."""

    def test_generate_all_creates_6_files(self, tmp_path: Path):
        """Test generate_all creates 6 command files (one for each command)."""
        config = WindsurfSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)
        assert len(created) == 6

    def test_generate_all_creates_files_in_windsurf_directory(self, tmp_path: Path):
        """Test generate_all creates files in .windsurf/workflows/ directory."""
        config = WindsurfSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        workflows_dir = tmp_path / ".windsurf" / "workflows"
        assert workflows_dir.exists()
        assert workflows_dir.is_dir()

    def test_generate_all_creates_plan_file(self, tmp_path: Path):
        """Test generate_all creates aurora-plan.md file."""
        config = WindsurfSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".windsurf" / "workflows" / "aurora-plan.md"
        assert plan_file.exists()

    def test_generate_all_file_has_frontmatter(self, tmp_path: Path):
        """Test generated file starts with YAML frontmatter."""
        config = WindsurfSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".windsurf" / "workflows" / "aurora-plan.md"
        content = plan_file.read_text()

        assert content.startswith("---")

    def test_generate_all_file_has_auto_execution_mode(self, tmp_path: Path):
        """Test generated file has auto_execution_mode: 3 in frontmatter."""
        config = WindsurfSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".windsurf" / "workflows" / "aurora-plan.md"
        content = plan_file.read_text()

        assert "auto_execution_mode: 3" in content

    def test_generate_all_file_has_aurora_markers(self, tmp_path: Path):
        """Test generated file contains Aurora markers."""
        config = WindsurfSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".windsurf" / "workflows" / "aurora-plan.md"
        content = plan_file.read_text()

        assert AURORA_MARKERS["start"] in content
        assert AURORA_MARKERS["end"] in content

    def test_generate_all_creates_all_command_files(self, tmp_path: Path):
        """Test generate_all creates all 7 command files with correct names."""
        config = WindsurfSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        workflows_dir = tmp_path / ".windsurf" / "workflows"
        for cmd_id in ALL_COMMANDS:
            filepath = workflows_dir / f"aurora-{cmd_id}.md"
            assert filepath.exists(), f"Expected file aurora-{cmd_id}.md to exist"

    def test_generate_all_returns_relative_paths(self, tmp_path: Path):
        """Test generate_all returns relative paths."""
        config = WindsurfSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        for path in created:
            assert not Path(path).is_absolute()
            assert path.startswith(".windsurf/workflows/")


class TestWindsurfSlashCommandConfiguratorUpdateExisting:
    """Tests for update_existing method."""

    def test_update_existing_preserves_custom_content(self, tmp_path: Path):
        """Test update_existing preserves custom content outside Aurora markers."""
        config = WindsurfSlashCommandConfigurator()

        # First generate the file
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".windsurf" / "workflows" / "aurora-plan.md"
        original_content = plan_file.read_text()

        # Add custom content outside markers
        frontmatter_end = original_content.find("---", 4) + 3

        custom_line = "\n\n<!-- Custom Windsurf workflow note -->\n"
        modified_content = (
            original_content[:frontmatter_end] + custom_line + original_content[frontmatter_end:]
        )
        plan_file.write_text(modified_content)

        # Now update existing
        config.update_existing(str(tmp_path), ".aurora")

        # Custom content should still be there
        updated_content = plan_file.read_text()
        assert "Custom Windsurf workflow note" in updated_content

    def test_update_existing_only_updates_existing_files(self, tmp_path: Path):
        """Test update_existing does not create new files."""
        config = WindsurfSlashCommandConfigurator()

        # Create only one file
        workflows_dir = tmp_path / ".windsurf" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        plan_file = workflows_dir / "aurora-plan.md"

        frontmatter = config.get_frontmatter("plan")
        plan_file.write_text(
            f"{frontmatter}\n{AURORA_MARKERS['start']}\nBody\n{AURORA_MARKERS['end']}\n"
        )

        # Update existing
        updated = config.update_existing(str(tmp_path), ".aurora")

        # Only the one file should be updated
        assert len(updated) == 1

        # Other files should NOT have been created
        query_file = workflows_dir / "aurora-query.md"
        assert not query_file.exists()


class TestWindsurfSlashCommandConfiguratorTargets:
    """Tests for get_targets method."""

    def test_get_targets_returns_6_targets(self):
        """Test get_targets returns 6 targets (one per command)."""
        config = WindsurfSlashCommandConfigurator()
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)
        assert len(targets) == 6

    def test_get_targets_returns_slash_command_targets(self):
        """Test get_targets returns SlashCommandTarget objects."""
        config = WindsurfSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    def test_get_targets_has_all_command_ids(self):
        """Test get_targets includes all command IDs."""
        config = WindsurfSlashCommandConfigurator()
        targets = config.get_targets()

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)

    def test_get_targets_paths_match_get_relative_path(self):
        """Test that target paths match get_relative_path output."""
        config = WindsurfSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            expected_path = config.get_relative_path(target.command_id)
            assert target.path == expected_path
