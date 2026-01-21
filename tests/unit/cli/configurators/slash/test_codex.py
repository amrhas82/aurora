"""Tests for CodexSlashCommandConfigurator.

Tests the Codex slash command configurator that creates commands
in a GLOBAL directory (~/.codex/prompts/ or $CODEX_HOME/prompts/)
rather than project-relative paths like other tools.
"""

import os
from pathlib import Path
from unittest.mock import patch

from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.codex import CodexSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


class TestCodexSlashCommandConfiguratorProperties:
    """Tests for basic properties of CodexSlashCommandConfigurator."""

    def test_tool_id_returns_codex(self):
        """Test that tool_id property returns 'codex'."""
        config = CodexSlashCommandConfigurator()
        assert config.tool_id == "codex"

    def test_is_available_returns_true(self):
        """Test that is_available property returns True.

        Codex is always available (doesn't require detection).
        """
        config = CodexSlashCommandConfigurator()
        assert config.is_available is True

    def test_inherits_from_slash_command_configurator(self):
        """Test that CodexSlashCommandConfigurator inherits from SlashCommandConfigurator."""
        assert issubclass(CodexSlashCommandConfigurator, SlashCommandConfigurator)

    def test_can_instantiate(self):
        """Test that CodexSlashCommandConfigurator can be instantiated."""
        config = CodexSlashCommandConfigurator()
        assert config is not None


class TestCodexSlashCommandConfiguratorGlobalPromptsDir:
    """Tests for _get_global_prompts_dir method."""

    def test_get_global_prompts_dir_default(self, tmp_path: Path):
        """Test _get_global_prompts_dir returns ~/.codex/prompts/ by default."""
        config = CodexSlashCommandConfigurator()

        # Clear CODEX_HOME if set
        with patch.dict(os.environ, {}, clear=True):
            # Also mock expanduser to use tmp_path
            with patch("os.path.expanduser") as mock_expanduser:
                mock_expanduser.return_value = str(tmp_path)
                prompts_dir = config._get_global_prompts_dir()

        assert prompts_dir.endswith("prompts")
        assert ".codex" in prompts_dir

    def test_get_global_prompts_dir_respects_codex_home(self, tmp_path: Path):
        """Test _get_global_prompts_dir respects CODEX_HOME environment variable."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "custom-codex")
        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            prompts_dir = config._get_global_prompts_dir()

        expected = str(Path(custom_codex_home) / "prompts")
        assert prompts_dir == expected

    def test_get_global_prompts_dir_strips_whitespace_from_codex_home(self, tmp_path: Path):
        """Test _get_global_prompts_dir strips whitespace from CODEX_HOME."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "custom-codex")
        with patch.dict(os.environ, {"CODEX_HOME": f"  {custom_codex_home}  "}):
            prompts_dir = config._get_global_prompts_dir()

        expected = str(Path(custom_codex_home) / "prompts")
        assert prompts_dir == expected

    def test_get_global_prompts_dir_ignores_empty_codex_home(self, tmp_path: Path):
        """Test _get_global_prompts_dir ignores empty CODEX_HOME."""
        config = CodexSlashCommandConfigurator()

        with patch.dict(os.environ, {"CODEX_HOME": ""}):
            with patch("os.path.expanduser") as mock_expanduser:
                mock_expanduser.return_value = str(tmp_path)
                prompts_dir = config._get_global_prompts_dir()

        # Should use default ~/.codex/prompts
        assert ".codex" in prompts_dir


class TestCodexSlashCommandConfiguratorPaths:
    """Tests for path-related methods."""

    def test_get_relative_path_plan(self):
        """Test get_relative_path returns correct relative path for 'plan' command."""
        config = CodexSlashCommandConfigurator()
        path = config.get_relative_path("plan")
        # Note: This is the relative path format, but Codex uses global paths
        assert path == ".codex/prompts/aurora-plan.md"

    def test_get_relative_path_all_commands(self):
        """Test get_relative_path works for all standard commands."""
        config = CodexSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(".codex/prompts/")
            assert path.endswith(".md")
            assert f"aurora-{cmd_id}" in path


class TestCodexSlashCommandConfiguratorResolveAbsolutePath:
    """Tests for resolve_absolute_path method (global path handling)."""

    def test_resolve_absolute_path_returns_global_path(self, tmp_path: Path):
        """Test resolve_absolute_path returns global path instead of project path."""
        config = CodexSlashCommandConfigurator()

        project_path = str(tmp_path / "my-project")
        custom_codex_home = str(tmp_path / "codex-home")

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            abs_path = config.resolve_absolute_path(project_path, "plan")

        # Should be in global directory, NOT project directory
        assert project_path not in abs_path
        assert custom_codex_home in abs_path
        assert abs_path == str(Path(custom_codex_home) / "prompts" / "aurora-plan.md")

    def test_resolve_absolute_path_ignores_project_path(self, tmp_path: Path):
        """Test resolve_absolute_path ignores the project_path parameter."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            # Different project paths should give same result
            abs_path1 = config.resolve_absolute_path("/project/a", "plan")
            abs_path2 = config.resolve_absolute_path("/project/b", "plan")

        assert abs_path1 == abs_path2

    def test_resolve_absolute_path_returns_absolute(self, tmp_path: Path):
        """Test resolve_absolute_path returns an absolute path."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()


class TestCodexSlashCommandConfiguratorFrontmatter:
    """Tests for frontmatter generation."""

    def test_get_frontmatter_plan_returns_yaml_with_arguments(self):
        """Test get_frontmatter returns YAML with $ARGUMENTS placeholder."""
        config = CodexSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert frontmatter is not None
        assert "$ARGUMENTS" in frontmatter

    def test_get_frontmatter_plan_has_description(self):
        """Test frontmatter contains 'description' field."""
        config = CodexSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "description:" in frontmatter

    def test_get_frontmatter_plan_has_argument_hint(self):
        """Test frontmatter contains 'argument-hint' field."""
        config = CodexSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "argument-hint:" in frontmatter

    def test_get_frontmatter_all_commands(self):
        """Test get_frontmatter works for all standard commands."""
        config = CodexSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            assert frontmatter is not None, f"Frontmatter for {cmd_id} should not be None"
            assert "$ARGUMENTS" in frontmatter, f"Frontmatter for {cmd_id} should have $ARGUMENTS"
            assert (
                "description:" in frontmatter
            ), f"Frontmatter for {cmd_id} should have description"
            assert (
                "argument-hint:" in frontmatter
            ), f"Frontmatter for {cmd_id} should have argument-hint"


class TestCodexSlashCommandConfiguratorBody:
    """Tests for body content generation."""

    def test_get_body_plan_returns_template(self):
        """Test get_body returns content from slash_commands templates."""
        config = CodexSlashCommandConfigurator()
        body = config.get_body("plan")

        expected = get_command_body("plan")
        assert body == expected

    def test_get_body_all_commands(self):
        """Test get_body works for all standard commands."""
        config = CodexSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            body = config.get_body(cmd_id)
            expected = get_command_body(cmd_id)
            assert body == expected, f"Body for {cmd_id} should match template"


class TestCodexSlashCommandConfiguratorGenerateAll:
    """Tests for generate_all method (writes to global directory)."""

    def test_generate_all_creates_3_files(self, tmp_path: Path):
        """Test generate_all creates 3 command files."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        project_path = str(tmp_path / "project")

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            created = config.generate_all(project_path, ".aurora")

        assert len(created) == len(ALL_COMMANDS)
        assert len(created) == 5

    def test_generate_all_writes_to_global_directory(self, tmp_path: Path):
        """Test generate_all writes to global directory, not project directory."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        project_path = str(tmp_path / "project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            config.generate_all(project_path, ".aurora")

        # Files should be in global directory
        prompts_dir = Path(custom_codex_home) / "prompts"
        assert prompts_dir.exists()

        plan_file = prompts_dir / "aurora-plan.md"
        assert plan_file.exists()

        # Files should NOT be in project directory
        project_prompts = Path(project_path) / ".codex" / "prompts"
        assert not project_prompts.exists()

    def test_generate_all_creates_prompts_directory(self, tmp_path: Path):
        """Test generate_all creates the prompts directory if it doesn't exist."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        project_path = str(tmp_path / "project")

        # prompts directory doesn't exist yet
        assert not Path(custom_codex_home).exists()

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            config.generate_all(project_path, ".aurora")

        # Directory should now exist
        prompts_dir = Path(custom_codex_home) / "prompts"
        assert prompts_dir.exists()

    def test_generate_all_file_has_frontmatter_with_arguments(self, tmp_path: Path):
        """Test generated file has frontmatter with $ARGUMENTS placeholder."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            config.generate_all(str(tmp_path), ".aurora")

        plan_file = Path(custom_codex_home) / "prompts" / "aurora-plan.md"
        content = plan_file.read_text()

        assert "$ARGUMENTS" in content

    def test_generate_all_file_has_aurora_markers(self, tmp_path: Path):
        """Test generated file contains Aurora markers."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            config.generate_all(str(tmp_path), ".aurora")

        plan_file = Path(custom_codex_home) / "prompts" / "aurora-plan.md"
        content = plan_file.read_text()

        assert AURORA_MARKERS["start"] in content
        assert AURORA_MARKERS["end"] in content

    def test_generate_all_creates_all_command_files(self, tmp_path: Path):
        """Test generate_all creates all 7 command files."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            config.generate_all(str(tmp_path), ".aurora")

        prompts_dir = Path(custom_codex_home) / "prompts"
        for cmd_id in ALL_COMMANDS:
            filepath = prompts_dir / f"aurora-{cmd_id}.md"
            assert filepath.exists(), f"Expected file aurora-{cmd_id}.md to exist"


class TestCodexSlashCommandConfiguratorUpdateExisting:
    """Tests for update_existing method."""

    def test_update_existing_only_updates_existing_files(self, tmp_path: Path):
        """Test update_existing only updates files that exist in global dir."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        prompts_dir = Path(custom_codex_home) / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # Create only one file
        plan_file = prompts_dir / "aurora-plan.md"
        frontmatter = config.get_frontmatter("plan")
        plan_file.write_text(
            f"{frontmatter}\n{AURORA_MARKERS['start']}\nOld body\n{AURORA_MARKERS['end']}\n"
        )

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            updated = config.update_existing(str(tmp_path), ".aurora")

        # Only the one file should be updated
        assert len(updated) == 1

        # Other files should NOT have been created
        query_file = prompts_dir / "aurora-query.md"
        assert not query_file.exists()

    def test_update_existing_updates_body_in_global_file(self, tmp_path: Path):
        """Test update_existing updates the body in the global file."""
        config = CodexSlashCommandConfigurator()

        custom_codex_home = str(tmp_path / "codex-home")
        prompts_dir = Path(custom_codex_home) / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # Create file with old body
        plan_file = prompts_dir / "aurora-plan.md"
        frontmatter = config.get_frontmatter("plan")
        old_body = "This is old content"
        plan_file.write_text(
            f"{frontmatter}\n{AURORA_MARKERS['start']}\n{old_body}\n{AURORA_MARKERS['end']}\n"
        )

        with patch.dict(os.environ, {"CODEX_HOME": custom_codex_home}):
            config.update_existing(str(tmp_path), ".aurora")

        # Old body should be gone, new body should be present
        updated_content = plan_file.read_text()
        assert old_body not in updated_content
        assert config.get_body("plan") in updated_content


class TestCodexSlashCommandConfiguratorTargets:
    """Tests for get_targets method."""

    def test_get_targets_returns_6_targets(self):
        """Test get_targets returns 5 targets (one per command)."""
        config = CodexSlashCommandConfigurator()
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)
        assert len(targets) == 5

    def test_get_targets_returns_slash_command_targets(self):
        """Test get_targets returns SlashCommandTarget objects."""
        config = CodexSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    def test_get_targets_has_all_command_ids(self):
        """Test get_targets includes all command IDs."""
        config = CodexSlashCommandConfigurator()
        targets = config.get_targets()

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)
