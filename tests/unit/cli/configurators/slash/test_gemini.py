"""Tests for GeminiSlashCommandConfigurator.

Tests the Gemini CLI slash command configurator that creates TOML-format
commands in .gemini/commands/aurora/ directory.
"""

from pathlib import Path

import pytest

# Python 3.11+ has tomllib built-in, but Python 3.10 needs tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]

from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.gemini import GeminiSlashCommandConfigurator
from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


class TestGeminiSlashCommandConfiguratorProperties:
    """Tests for basic properties of GeminiSlashCommandConfigurator."""

    def test_tool_id_returns_gemini(self):
        """Test that tool_id property returns 'gemini'."""
        config = GeminiSlashCommandConfigurator()
        assert config.tool_id == "gemini"

    def test_is_available_returns_true(self):
        """Test that is_available property returns True.

        Gemini is always available (doesn't require detection).
        """
        config = GeminiSlashCommandConfigurator()
        assert config.is_available is True

    def test_inherits_from_toml_slash_command_configurator(self):
        """Test that GeminiSlashCommandConfigurator extends TomlSlashCommandConfigurator."""
        assert issubclass(GeminiSlashCommandConfigurator, TomlSlashCommandConfigurator)

    def test_inherits_from_slash_command_configurator(self):
        """Test that GeminiSlashCommandConfigurator inherits from SlashCommandConfigurator."""
        assert issubclass(GeminiSlashCommandConfigurator, SlashCommandConfigurator)

    def test_can_instantiate(self):
        """Test that GeminiSlashCommandConfigurator can be instantiated."""
        config = GeminiSlashCommandConfigurator()
        assert config is not None


class TestGeminiSlashCommandConfiguratorPaths:
    """Tests for path-related methods."""

    def test_get_relative_path_plan(self):
        """Test get_relative_path returns correct path for 'plan' command."""
        config = GeminiSlashCommandConfigurator()
        path = config.get_relative_path("plan")
        assert path == ".gemini/commands/aurora/plan.toml"

    def test_get_relative_path_all_commands(self):
        """Test get_relative_path works for all standard commands."""
        config = GeminiSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(".gemini/commands/aurora/")
            assert path.endswith(".toml")
            assert cmd_id in path

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Test resolve_absolute_path returns absolute path."""
        config = GeminiSlashCommandConfigurator()
        abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()
        expected = str(tmp_path / ".gemini/commands/aurora/plan.toml")
        assert abs_path == expected


class TestGeminiSlashCommandConfiguratorDescription:
    """Tests for get_description method."""

    def test_get_description_plan_returns_string(self):
        """Test get_description returns a non-empty string for 'plan' command."""
        config = GeminiSlashCommandConfigurator()
        desc = config.get_description("plan")

        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_description_all_commands(self):
        """Test get_description works for all standard commands."""
        config = GeminiSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            desc = config.get_description(cmd_id)
            assert isinstance(desc, str)
            assert len(desc) > 0, f"Description for {cmd_id} should not be empty"


class TestGeminiSlashCommandConfiguratorFrontmatter:
    """Tests for frontmatter behavior (TOML has no frontmatter)."""

    def test_get_frontmatter_returns_none(self):
        """Test get_frontmatter returns None for TOML format.

        TOML format embeds all metadata in the TOML structure itself.
        """
        config = GeminiSlashCommandConfigurator()
        result = config.get_frontmatter("plan")
        assert result is None

    def test_get_frontmatter_returns_none_for_all_commands(self):
        """Test get_frontmatter returns None for all commands."""
        config = GeminiSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            result = config.get_frontmatter(cmd_id)
            assert result is None, f"Expected None for command {cmd_id}"


class TestGeminiSlashCommandConfiguratorBody:
    """Tests for body content generation."""

    def test_get_body_plan_returns_template(self):
        """Test get_body returns content from slash_commands templates."""
        config = GeminiSlashCommandConfigurator()
        body = config.get_body("plan")

        expected = get_command_body("plan")
        assert body == expected

    def test_get_body_all_commands(self):
        """Test get_body works for all standard commands."""
        config = GeminiSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            body = config.get_body(cmd_id)
            expected = get_command_body(cmd_id)
            assert body == expected, f"Body for {cmd_id} should match template"


class TestGeminiSlashCommandConfiguratorGenerateAll:
    """Tests for generate_all method with TOML output."""

    def test_generate_all_creates_6_files(self, tmp_path: Path):
        """Test generate_all creates 6 command files (one for each command)."""
        config = GeminiSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)
        assert len(created) == 6

    def test_generate_all_creates_toml_files(self, tmp_path: Path):
        """Test generate_all creates .toml files."""
        config = GeminiSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            assert file_path.exists(), f"File for {cmd_id} should exist"
            assert file_path.suffix == ".toml", f"File for {cmd_id} should have .toml extension"

    def test_generate_all_creates_valid_toml_syntax(self, tmp_path: Path):
        """Test generated files have valid TOML syntax."""
        config = GeminiSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            content = file_path.read_text()

            try:
                parsed = tomllib.loads(content)
            except Exception as e:
                pytest.fail(f"File for {cmd_id} is not valid TOML: {e}")

            assert "description" in parsed, f"TOML for {cmd_id} should have 'description' field"
            assert "prompt" in parsed, f"TOML for {cmd_id} should have 'prompt' field"

    def test_generate_all_has_description_field(self, tmp_path: Path):
        """Test TOML output has description = '...' field."""
        config = GeminiSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        content = file_path.read_text()

        assert 'description = "' in content
        expected_desc = config.get_description("plan")
        assert expected_desc in content

    def test_generate_all_has_prompt_field_with_triple_quotes(self, tmp_path: Path):
        """Test TOML output has prompt = '''...''' field."""
        config = GeminiSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        content = file_path.read_text()

        assert 'prompt = """' in content

    def test_generate_all_has_markers_inside_prompt(self, tmp_path: Path):
        """Test Aurora markers are inside the prompt triple-quoted string."""
        config = GeminiSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        content = file_path.read_text()

        # Find the prompt section
        prompt_start = content.find('prompt = """')
        assert prompt_start != -1, "Should have prompt field"

        # Markers should appear after prompt start
        start_marker_pos = content.find(AURORA_MARKERS["start"])
        end_marker_pos = content.find(AURORA_MARKERS["end"])

        assert start_marker_pos > prompt_start, "Start marker should be inside prompt"
        assert end_marker_pos > start_marker_pos, "End marker should be after start marker"

    def test_generate_all_returns_relative_paths(self, tmp_path: Path):
        """Test generate_all returns relative paths."""
        config = GeminiSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        for path in created:
            assert not Path(path).is_absolute()
            assert path.endswith(".toml")

    def test_generate_all_creates_directory_structure(self, tmp_path: Path):
        """Test generate_all creates the directory structure."""
        config = GeminiSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        commands_dir = tmp_path / ".gemini" / "commands" / "aurora"
        assert commands_dir.exists()
        assert commands_dir.is_dir()


class TestGeminiSlashCommandConfiguratorUpdateExisting:
    """Tests for update_existing method."""

    def test_update_existing_preserves_custom_description(self, tmp_path: Path):
        """Test update_existing preserves custom description outside markers."""
        config = GeminiSlashCommandConfigurator()

        # Create file with custom description
        plan_dir = tmp_path / ".gemini" / "commands" / "aurora"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "plan.toml"

        plan_file.write_text(
            f'''description = "My Custom Description"

prompt = """
{AURORA_MARKERS["start"]}
Old body content
{AURORA_MARKERS["end"]}
"""
'''
        )

        config.update_existing(str(tmp_path), ".aurora")

        # Custom description should be preserved
        updated_content = plan_file.read_text()
        assert 'description = "My Custom Description"' in updated_content

    def test_update_existing_updates_body_between_markers(self, tmp_path: Path):
        """Test update_existing updates the body content between markers."""
        config = GeminiSlashCommandConfigurator()

        # Create file with old body content
        plan_dir = tmp_path / ".gemini" / "commands" / "aurora"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "plan.toml"

        old_body = "This is old body content that should be replaced."
        plan_file.write_text(
            f'''description = "Test description"

prompt = """
{AURORA_MARKERS["start"]}
{old_body}
{AURORA_MARKERS["end"]}
"""
'''
        )

        config.update_existing(str(tmp_path), ".aurora")

        # Old body should be gone, new body should be present
        updated_content = plan_file.read_text()
        assert old_body not in updated_content
        assert config.get_body("plan") in updated_content

    def test_update_existing_only_updates_existing_files(self, tmp_path: Path):
        """Test update_existing does not create new files."""
        config = GeminiSlashCommandConfigurator()

        # Create only one file
        plan_dir = tmp_path / ".gemini" / "commands" / "aurora"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "plan.toml"

        plan_file.write_text(
            f'''description = "Test"

prompt = """
{AURORA_MARKERS["start"]}
Body
{AURORA_MARKERS["end"]}
"""
'''
        )

        updated = config.update_existing(str(tmp_path), ".aurora")

        assert len(updated) == 1
        assert ".gemini/commands/aurora/plan.toml" in updated

        # Other files should NOT have been created
        query_file = plan_dir / "query.toml"
        assert not query_file.exists()


class TestGeminiSlashCommandConfiguratorTargets:
    """Tests for get_targets method."""

    def test_get_targets_returns_6_targets(self):
        """Test get_targets returns 6 targets (one per command)."""
        config = GeminiSlashCommandConfigurator()
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)
        assert len(targets) == 6

    def test_get_targets_returns_slash_command_targets(self):
        """Test get_targets returns SlashCommandTarget objects."""
        config = GeminiSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    def test_get_targets_paths_end_with_toml(self):
        """Test all target paths end with .toml extension."""
        config = GeminiSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert target.path.endswith(".toml"), f"Path {target.path} should end with .toml"

    def test_get_targets_has_all_command_ids(self):
        """Test get_targets includes all command IDs."""
        config = GeminiSlashCommandConfigurator()
        targets = config.get_targets()

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)
