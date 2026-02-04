"""Tests for TomlSlashCommandConfigurator base class.

Tests the TOML-format base class used by tools like Gemini CLI that require
TOML configuration files instead of markdown.
"""

from pathlib import Path

import pytest

# Python 3.11+ has tomllib built-in, but Python 3.10 needs tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]

from aurora_cli.configurators.slash.base import ALL_COMMANDS, AURORA_MARKERS, SlashCommandTarget
from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator


class ConcreteTomlConfigurator(TomlSlashCommandConfigurator):
    """Concrete implementation for testing the abstract TomlSlashCommandConfigurator."""

    DESCRIPTIONS = {
        "plan": "Create and manage project plans",
        "query": "Query the codebase using semantic search",
        "index": "Index codebase for semantic search",
        "search": "Search indexed code",
        "init": "Initialize Aurora for the project",
        "doctor": "Run health checks",
        "agents": "Browse and search AI agents",
    }

    FILE_PATHS = {
        "plan": ".test-tool/commands/aurora/plan.toml",
        "query": ".test-tool/commands/aurora/query.toml",
        "index": ".test-tool/commands/aurora/index.toml",
        "search": ".test-tool/commands/aurora/search.toml",
        "init": ".test-tool/commands/aurora/init.toml",
        "doctor": ".test-tool/commands/aurora/doctor.toml",
        "agents": ".test-tool/commands/aurora/agents.toml",
    }

    @property
    def tool_id(self) -> str:
        return "test-toml-tool"

    @property
    def is_available(self) -> bool:
        return True

    def get_relative_path(self, command_id: str) -> str:
        return self.FILE_PATHS.get(command_id, f".test-tool/commands/aurora/{command_id}.toml")

    def get_description(self, command_id: str) -> str:
        return self.DESCRIPTIONS.get(command_id, f"Aurora {command_id} command")

    def get_body(self, command_id: str) -> str:
        return f"This is the body content for {command_id} command."


class TestTomlSlashCommandConfiguratorAbstract:
    """Tests for abstract method requirements."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that TomlSlashCommandConfigurator cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            TomlSlashCommandConfigurator()  # type: ignore

    def test_get_description_is_abstract(self):
        """Test that get_description must be implemented by subclasses."""
        # This is implicitly tested by the concrete class, but we verify
        # the abstract method exists
        assert hasattr(TomlSlashCommandConfigurator, "get_description")

        # Verify it's declared abstract (will have __isabstractmethod__ = True)

        # Get the method from the class
        method = getattr(TomlSlashCommandConfigurator, "get_description", None)
        assert method is not None
        assert getattr(method, "__isabstractmethod__", False) is True


class TestTomlSlashCommandConfiguratorFrontmatter:
    """Tests for frontmatter behavior in TOML configurators."""

    def test_get_frontmatter_returns_none(self):
        """Test that get_frontmatter returns None for TOML format.

        TOML format embeds all metadata in the TOML structure itself,
        so there's no separate frontmatter section.
        """
        config = ConcreteTomlConfigurator()
        result = config.get_frontmatter("plan")
        assert result is None

    def test_get_frontmatter_returns_none_for_all_commands(self):
        """Test that get_frontmatter returns None for all commands."""
        config = ConcreteTomlConfigurator()

        for cmd_id in ALL_COMMANDS:
            result = config.get_frontmatter(cmd_id)
            assert result is None, f"Expected None for command {cmd_id}"


class TestTomlSlashCommandConfiguratorDescription:
    """Tests for the get_description abstract method."""

    def test_get_description_returns_string(self):
        """Test that get_description returns a non-empty string."""
        config = ConcreteTomlConfigurator()
        result = config.get_description("plan")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_description_for_all_commands(self):
        """Test that get_description works for all standard commands."""
        config = ConcreteTomlConfigurator()

        for cmd_id in ALL_COMMANDS:
            result = config.get_description(cmd_id)
            assert isinstance(result, str)
            assert len(result) > 0, f"Description for {cmd_id} should not be empty"


class TestTomlSlashCommandConfiguratorGenerateAll:
    """Tests for generate_all method with TOML output."""

    def test_generate_all_creates_toml_files(self, tmp_path: Path):
        """Test that generate_all creates .toml files."""
        config = ConcreteTomlConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            assert file_path.exists(), f"File for {cmd_id} should exist"
            assert file_path.suffix == ".toml", f"File for {cmd_id} should have .toml extension"

    def test_generate_all_creates_valid_toml_syntax(self, tmp_path: Path):
        """Test that generated files have valid TOML syntax."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            content = file_path.read_text()

            # Should be parseable as TOML
            try:
                parsed = tomllib.loads(content)
            except Exception as e:
                pytest.fail(f"File for {cmd_id} is not valid TOML: {e}")

            assert "description" in parsed, f"TOML for {cmd_id} should have 'description' field"
            assert "prompt" in parsed, f"TOML for {cmd_id} should have 'prompt' field"

    def test_generate_all_has_description_field(self, tmp_path: Path):
        """Test that TOML output has description = '...' field."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        content = file_path.read_text()

        # Should contain description field with the expected value
        assert 'description = "' in content
        expected_desc = config.get_description("plan")
        assert expected_desc in content

    def test_generate_all_has_prompt_field_with_triple_quotes(self, tmp_path: Path):
        """Test that TOML output has prompt = '''...''' field."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        content = file_path.read_text()

        # Should contain prompt field with triple quotes for multi-line string
        assert 'prompt = """' in content

    def test_generate_all_has_markers_inside_prompt(self, tmp_path: Path):
        """Test that Aurora markers are inside the prompt triple-quoted string."""
        config = ConcreteTomlConfigurator()
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

    def test_generate_all_has_body_between_markers(self, tmp_path: Path):
        """Test that command body is between the Aurora markers."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        content = file_path.read_text()

        # Extract content between markers
        start_marker = AURORA_MARKERS["start"]
        end_marker = AURORA_MARKERS["end"]

        start_idx = content.find(start_marker) + len(start_marker)
        end_idx = content.find(end_marker)

        between_markers = content[start_idx:end_idx].strip()
        expected_body = config.get_body("plan")

        assert expected_body in between_markers

    def test_generate_all_returns_relative_paths(self, tmp_path: Path):
        """Test that generate_all returns relative paths, not absolute."""
        config = ConcreteTomlConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        for path in created:
            assert not Path(path).is_absolute(), f"Path {path} should be relative"
            assert path.endswith(".toml"), f"Path {path} should end with .toml"

    def test_generate_all_creates_parent_directories(self, tmp_path: Path):
        """Test that generate_all creates parent directories if needed."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        # Verify nested directory structure was created
        commands_dir = tmp_path / ".test-tool" / "commands" / "aurora"
        assert commands_dir.exists()
        assert commands_dir.is_dir()


class TestTomlSlashCommandConfiguratorUpdateBody:
    """Tests for _update_body method with TOML format."""

    def test_update_body_replaces_content_between_markers(self, tmp_path: Path):
        """Test that _update_body correctly replaces content between markers in TOML."""
        config = ConcreteTomlConfigurator()

        # First generate files
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        original_content = file_path.read_text()

        # Now update with new body
        new_body = "This is the UPDATED body content for testing."
        config._update_body(str(file_path), new_body)

        updated_content = file_path.read_text()

        # Old body should be gone
        old_body = config.get_body("plan")
        assert old_body not in updated_content

        # New body should be present
        assert new_body in updated_content

        # Markers should still be present
        assert AURORA_MARKERS["start"] in updated_content
        assert AURORA_MARKERS["end"] in updated_content

    def test_update_body_preserves_toml_structure(self, tmp_path: Path):
        """Test that _update_body preserves TOML structure outside markers."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")

        # Update body
        new_body = "Updated body content."
        config._update_body(str(file_path), new_body)

        # Should still be valid TOML
        updated_content = file_path.read_text()
        try:
            parsed = tomllib.loads(updated_content)
        except Exception as e:
            pytest.fail(f"Updated file is not valid TOML: {e}")

        # Description should be preserved
        assert "description" in parsed
        assert parsed["description"] == config.get_description("plan")

    def test_update_body_preserves_description(self, tmp_path: Path):
        """Test that _update_body preserves the description field."""
        config = ConcreteTomlConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        file_path = tmp_path / config.get_relative_path("plan")
        expected_desc = config.get_description("plan")

        # Update body
        config._update_body(str(file_path), "New body content")

        updated_content = file_path.read_text()
        assert f'description = "{expected_desc}"' in updated_content

    def test_update_body_raises_error_if_markers_missing(self, tmp_path: Path):
        """Test that _update_body raises ValueError if markers are missing."""
        config = ConcreteTomlConfigurator()

        # Create file without markers
        file_path = tmp_path / "no_markers.toml"
        file_path.write_text('description = "test"\nprompt = """content without markers"""')

        with pytest.raises(ValueError, match="Missing Aurora markers"):
            config._update_body(str(file_path), "new body")

    def test_update_body_raises_error_if_only_start_marker(self, tmp_path: Path):
        """Test that _update_body raises error if only start marker present."""
        config = ConcreteTomlConfigurator()

        file_path = tmp_path / "partial_markers.toml"
        file_path.write_text(
            f'description = "test"\nprompt = """\n{AURORA_MARKERS["start"]}\ncontent\n"""',
        )

        with pytest.raises(ValueError, match="Missing Aurora markers"):
            config._update_body(str(file_path), "new body")

    def test_update_body_raises_error_if_only_end_marker(self, tmp_path: Path):
        """Test that _update_body raises error if only end marker present."""
        config = ConcreteTomlConfigurator()

        file_path = tmp_path / "partial_markers.toml"
        file_path.write_text(
            f'description = "test"\nprompt = """\ncontent\n{AURORA_MARKERS["end"]}\n"""',
        )

        with pytest.raises(ValueError, match="Missing Aurora markers"):
            config._update_body(str(file_path), "new body")


class TestTomlSlashCommandConfiguratorUpdateExisting:
    """Tests for update_existing method."""

    def test_update_existing_only_updates_existing_files(self, tmp_path: Path):
        """Test that update_existing only updates files that already exist."""
        config = ConcreteTomlConfigurator()

        # Create only one file manually
        plan_path = tmp_path / config.get_relative_path("plan")
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            f'''description = "Old description"

prompt = """
{AURORA_MARKERS["start"]}
Old body content
{AURORA_MARKERS["end"]}
"""
''',
        )

        # update_existing should only update the one file that exists
        updated = config.update_existing(str(tmp_path), ".aurora")

        assert len(updated) == 1
        assert config.get_relative_path("plan") in updated

        # Other files should NOT have been created
        query_path = tmp_path / config.get_relative_path("query")
        assert not query_path.exists()

    def test_update_existing_preserves_custom_description(self, tmp_path: Path):
        """Test that update_existing preserves custom description outside markers."""
        config = ConcreteTomlConfigurator()

        # Create file with custom description
        plan_path = tmp_path / config.get_relative_path("plan")
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            f'''description = "My Custom Description"

prompt = """
{AURORA_MARKERS["start"]}
Old body content
{AURORA_MARKERS["end"]}
"""
''',
        )

        config.update_existing(str(tmp_path), ".aurora")

        # Custom description should be preserved
        updated_content = plan_path.read_text()
        assert 'description = "My Custom Description"' in updated_content

    def test_update_existing_returns_empty_if_no_files(self, tmp_path: Path):
        """Test that update_existing returns empty list if no files exist."""
        config = ConcreteTomlConfigurator()
        updated = config.update_existing(str(tmp_path), ".aurora")

        assert updated == []


class TestTomlSlashCommandConfiguratorTargets:
    """Tests for get_targets method."""

    def test_get_targets_returns_all_commands(self):
        """Test that get_targets returns targets for all commands."""
        config = ConcreteTomlConfigurator()
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)

    def test_get_targets_returns_slash_command_targets(self):
        """Test that get_targets returns SlashCommandTarget objects."""
        config = ConcreteTomlConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    def test_get_targets_paths_end_with_toml(self):
        """Test that all target paths end with .toml extension."""
        config = ConcreteTomlConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert target.path.endswith(".toml"), f"Path {target.path} should end with .toml"


class TestTomlSlashCommandConfiguratorInheritance:
    """Tests for proper inheritance from SlashCommandConfigurator."""

    def test_inherits_from_slash_command_configurator(self):
        """Test that TomlSlashCommandConfigurator inherits from SlashCommandConfigurator."""
        from aurora_cli.configurators.slash.base import SlashCommandConfigurator

        assert issubclass(TomlSlashCommandConfigurator, SlashCommandConfigurator)

    def test_concrete_implementation_inherits_from_toml_base(self):
        """Test that concrete implementation inherits from TomlSlashCommandConfigurator."""
        assert issubclass(ConcreteTomlConfigurator, TomlSlashCommandConfigurator)

    def test_resolve_absolute_path_works(self, tmp_path: Path):
        """Test that inherited resolve_absolute_path method works correctly."""
        config = ConcreteTomlConfigurator()
        abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()
        assert abs_path == str(tmp_path / config.get_relative_path("plan"))
