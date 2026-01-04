"""Tests for ClaudeSlashCommandConfigurator.

Tests the Claude Code slash command configurator that creates commands
in .claude/commands/aur/ directory.
"""

from pathlib import Path

import pytest
from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.claude import ClaudeSlashCommandConfigurator
from aurora_cli.templates.slash_commands import get_command_body


class TestClaudeSlashCommandConfiguratorProperties:
    """Tests for basic properties of ClaudeSlashCommandConfigurator."""

    def test_tool_id_returns_claude(self):
        """Test that tool_id property returns 'claude'."""
        config = ClaudeSlashCommandConfigurator()
        assert config.tool_id == "claude"

    def test_is_available_returns_true(self):
        """Test that is_available property returns True.

        Claude Code is always available (doesn't require detection).
        """
        config = ClaudeSlashCommandConfigurator()
        assert config.is_available is True

    def test_inherits_from_slash_command_configurator(self):
        """Test that ClaudeSlashCommandConfigurator inherits from SlashCommandConfigurator."""
        assert issubclass(ClaudeSlashCommandConfigurator, SlashCommandConfigurator)

    def test_can_instantiate(self):
        """Test that ClaudeSlashCommandConfigurator can be instantiated."""
        config = ClaudeSlashCommandConfigurator()
        assert config is not None


class TestClaudeSlashCommandConfiguratorPaths:
    """Tests for path-related methods."""

    def test_get_relative_path_plan(self):
        """Test get_relative_path returns correct path for 'plan' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("plan")
        assert path == ".claude/commands/aur/plan.md"

    def test_get_relative_path_query(self):
        """Test get_relative_path returns correct path for 'query' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("query")
        assert path == ".claude/commands/aur/query.md"

    def test_get_relative_path_index(self):
        """Test get_relative_path returns correct path for 'index' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("index")
        assert path == ".claude/commands/aur/index.md"

    def test_get_relative_path_search(self):
        """Test get_relative_path returns correct path for 'search' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("search")
        assert path == ".claude/commands/aur/search.md"

    def test_get_relative_path_init(self):
        """Test get_relative_path returns correct path for 'init' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("init")
        assert path == ".claude/commands/aur/init.md"

    def test_get_relative_path_doctor(self):
        """Test get_relative_path returns correct path for 'doctor' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("doctor")
        assert path == ".claude/commands/aur/doctor.md"

    def test_get_relative_path_agents(self):
        """Test get_relative_path returns correct path for 'agents' command."""
        config = ClaudeSlashCommandConfigurator()
        path = config.get_relative_path("agents")
        assert path == ".claude/commands/aur/agents.md"

    def test_get_relative_path_all_commands(self):
        """Test get_relative_path works for all standard commands."""
        config = ClaudeSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(".claude/commands/aur/")
            assert path.endswith(".md")
            assert cmd_id in path

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Test resolve_absolute_path returns absolute path."""
        config = ClaudeSlashCommandConfigurator()
        abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()
        expected = str(tmp_path / ".claude/commands/aur/plan.md")
        assert abs_path == expected


class TestClaudeSlashCommandConfiguratorFrontmatter:
    """Tests for frontmatter generation."""

    def test_get_frontmatter_plan_returns_yaml(self):
        """Test get_frontmatter returns YAML frontmatter for 'plan' command."""
        config = ClaudeSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert frontmatter is not None
        assert frontmatter.startswith("---")
        assert frontmatter.endswith("---")

    def test_get_frontmatter_plan_has_name(self):
        """Test frontmatter contains 'name' field."""
        config = ClaudeSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "name:" in frontmatter
        assert "Aurora" in frontmatter

    def test_get_frontmatter_plan_has_description(self):
        """Test frontmatter contains 'description' field."""
        config = ClaudeSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "description:" in frontmatter

    def test_get_frontmatter_plan_has_category(self):
        """Test frontmatter contains 'category' field."""
        config = ClaudeSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "category:" in frontmatter
        assert "Aurora" in frontmatter

    def test_get_frontmatter_plan_has_tags(self):
        """Test frontmatter contains 'tags' field."""
        config = ClaudeSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("plan")

        assert "tags:" in frontmatter
        assert "aurora" in frontmatter.lower()

    def test_get_frontmatter_all_commands(self):
        """Test get_frontmatter works for all standard commands."""
        config = ClaudeSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            assert frontmatter is not None, f"Frontmatter for {cmd_id} should not be None"
            assert "---" in frontmatter, f"Frontmatter for {cmd_id} should have YAML delimiters"
            assert "name:" in frontmatter, f"Frontmatter for {cmd_id} should have name"
            assert "description:" in frontmatter, f"Frontmatter for {cmd_id} should have description"

    def test_get_frontmatter_query_has_memory_tags(self):
        """Test query command frontmatter includes memory-related tags."""
        config = ClaudeSlashCommandConfigurator()
        frontmatter = config.get_frontmatter("query")

        assert "memory" in frontmatter.lower() or "search" in frontmatter.lower()


class TestClaudeSlashCommandConfiguratorBody:
    """Tests for body content generation."""

    def test_get_body_plan_returns_template(self):
        """Test get_body returns content from slash_commands templates."""
        config = ClaudeSlashCommandConfigurator()
        body = config.get_body("plan")

        # Should return the same content as get_command_body
        expected = get_command_body("plan")
        assert body == expected

    def test_get_body_query_returns_template(self):
        """Test get_body returns content for query command."""
        config = ClaudeSlashCommandConfigurator()
        body = config.get_body("query")

        expected = get_command_body("query")
        assert body == expected

    def test_get_body_all_commands(self):
        """Test get_body works for all standard commands."""
        config = ClaudeSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            body = config.get_body(cmd_id)
            expected = get_command_body(cmd_id)
            assert body == expected, f"Body for {cmd_id} should match template"

    def test_get_body_contains_guardrails(self):
        """Test body content contains guardrails section."""
        config = ClaudeSlashCommandConfigurator()
        body = config.get_body("plan")

        assert "Guardrails" in body or "guardrails" in body.lower()


class TestClaudeSlashCommandConfiguratorGenerateAll:
    """Tests for generate_all method."""

    def test_generate_all_creates_7_files(self, tmp_path: Path):
        """Test generate_all creates 7 command files (one for each command)."""
        config = ClaudeSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)
        assert len(created) == 7

    def test_generate_all_creates_files_in_claude_directory(self, tmp_path: Path):
        """Test generate_all creates files in .claude/commands/aur/ directory."""
        config = ClaudeSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        aur_dir = tmp_path / ".claude" / "commands" / "aur"
        assert aur_dir.exists()
        assert aur_dir.is_dir()

    def test_generate_all_creates_plan_file(self, tmp_path: Path):
        """Test generate_all creates plan.md file."""
        config = ClaudeSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".claude" / "commands" / "aur" / "plan.md"
        assert plan_file.exists()

    def test_generate_all_file_has_frontmatter(self, tmp_path: Path):
        """Test generated file starts with YAML frontmatter."""
        config = ClaudeSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".claude" / "commands" / "aur" / "plan.md"
        content = plan_file.read_text()

        assert content.startswith("---")

    def test_generate_all_file_has_aurora_markers(self, tmp_path: Path):
        """Test generated file contains Aurora markers."""
        config = ClaudeSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".claude" / "commands" / "aur" / "plan.md"
        content = plan_file.read_text()

        assert AURORA_MARKERS["start"] in content
        assert AURORA_MARKERS["end"] in content

    def test_generate_all_file_has_body_between_markers(self, tmp_path: Path):
        """Test generated file has body content between Aurora markers."""
        config = ClaudeSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".claude" / "commands" / "aur" / "plan.md"
        content = plan_file.read_text()

        # Extract content between markers
        start_idx = content.find(AURORA_MARKERS["start"]) + len(AURORA_MARKERS["start"])
        end_idx = content.find(AURORA_MARKERS["end"])
        between_markers = content[start_idx:end_idx].strip()

        expected_body = config.get_body("plan")
        assert expected_body in between_markers

    def test_generate_all_returns_relative_paths(self, tmp_path: Path):
        """Test generate_all returns relative paths."""
        config = ClaudeSlashCommandConfigurator()
        created = config.generate_all(str(tmp_path), ".aurora")

        for path in created:
            assert not Path(path).is_absolute()
            assert path.startswith(".claude/commands/aur/")

    def test_generate_all_creates_all_7_command_files(self, tmp_path: Path):
        """Test generate_all creates all 7 command files."""
        config = ClaudeSlashCommandConfigurator()
        config.generate_all(str(tmp_path), ".aurora")

        expected_files = [
            "plan.md", "query.md", "index.md", "search.md",
            "init.md", "doctor.md", "agents.md"
        ]

        aur_dir = tmp_path / ".claude" / "commands" / "aur"
        for filename in expected_files:
            filepath = aur_dir / filename
            assert filepath.exists(), f"Expected file {filename} to exist"


class TestClaudeSlashCommandConfiguratorUpdateExisting:
    """Tests for update_existing method."""

    def test_update_existing_preserves_custom_content_outside_markers(self, tmp_path: Path):
        """Test update_existing preserves custom content outside Aurora markers."""
        config = ClaudeSlashCommandConfigurator()

        # First generate the file
        config.generate_all(str(tmp_path), ".aurora")

        plan_file = tmp_path / ".claude" / "commands" / "aur" / "plan.md"
        original_content = plan_file.read_text()

        # Add custom content outside markers (after the frontmatter, before markers)
        # Find the end of frontmatter
        frontmatter_end = original_content.find("---", 4) + 3  # Skip first ---

        # Insert custom content between frontmatter and markers
        custom_line = "\n\n<!-- Custom user note: Do not delete! -->\n"
        modified_content = (
            original_content[:frontmatter_end]
            + custom_line
            + original_content[frontmatter_end:]
        )
        plan_file.write_text(modified_content)

        # Now update existing
        config.update_existing(str(tmp_path), ".aurora")

        # Custom content should still be there
        updated_content = plan_file.read_text()
        assert "Custom user note" in updated_content

    def test_update_existing_updates_body_between_markers(self, tmp_path: Path):
        """Test update_existing updates the body content between markers."""
        config = ClaudeSlashCommandConfigurator()

        # Create file with old body content
        plan_dir = tmp_path / ".claude" / "commands" / "aur"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "plan.md"

        frontmatter = config.get_frontmatter("plan")
        old_body = "This is old body content that should be replaced."

        plan_file.write_text(
            f"{frontmatter}\n"
            f"{AURORA_MARKERS['start']}\n"
            f"{old_body}\n"
            f"{AURORA_MARKERS['end']}\n"
        )

        # Update existing
        config.update_existing(str(tmp_path), ".aurora")

        # Old body should be gone, new body should be present
        updated_content = plan_file.read_text()
        assert old_body not in updated_content
        assert config.get_body("plan") in updated_content

    def test_update_existing_preserves_frontmatter(self, tmp_path: Path):
        """Test update_existing preserves custom frontmatter modifications."""
        config = ClaudeSlashCommandConfigurator()

        # Create file with custom frontmatter
        plan_dir = tmp_path / ".claude" / "commands" / "aur"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "plan.md"

        custom_frontmatter = """---
name: My Custom Name
description: My custom description
category: Custom Category
tags: [custom, tags]
custom_field: custom_value
---"""

        plan_file.write_text(
            f"{custom_frontmatter}\n"
            f"{AURORA_MARKERS['start']}\n"
            f"Old body\n"
            f"{AURORA_MARKERS['end']}\n"
        )

        # Update existing
        config.update_existing(str(tmp_path), ".aurora")

        # Custom frontmatter should be preserved
        updated_content = plan_file.read_text()
        assert "My Custom Name" in updated_content
        assert "custom_field:" in updated_content

    def test_update_existing_returns_list_of_updated_files(self, tmp_path: Path):
        """Test update_existing returns list of files that were updated."""
        config = ClaudeSlashCommandConfigurator()

        # Generate all files first
        config.generate_all(str(tmp_path), ".aurora")

        # Update existing
        updated = config.update_existing(str(tmp_path), ".aurora")

        assert isinstance(updated, list)
        assert len(updated) == len(ALL_COMMANDS)

    def test_update_existing_only_updates_existing_files(self, tmp_path: Path):
        """Test update_existing does not create new files."""
        config = ClaudeSlashCommandConfigurator()

        # Create only one file
        plan_dir = tmp_path / ".claude" / "commands" / "aur"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file = plan_dir / "plan.md"

        frontmatter = config.get_frontmatter("plan")
        plan_file.write_text(
            f"{frontmatter}\n"
            f"{AURORA_MARKERS['start']}\n"
            f"Body\n"
            f"{AURORA_MARKERS['end']}\n"
        )

        # Update existing
        updated = config.update_existing(str(tmp_path), ".aurora")

        # Only the one file should be updated
        assert len(updated) == 1
        assert ".claude/commands/aur/plan.md" in updated

        # Other files should NOT have been created
        query_file = plan_dir / "query.md"
        assert not query_file.exists()


class TestClaudeSlashCommandConfiguratorTargets:
    """Tests for get_targets method."""

    def test_get_targets_returns_7_targets(self):
        """Test get_targets returns 7 targets (one per command)."""
        config = ClaudeSlashCommandConfigurator()
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)
        assert len(targets) == 7

    def test_get_targets_returns_slash_command_targets(self):
        """Test get_targets returns SlashCommandTarget objects."""
        config = ClaudeSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    def test_get_targets_has_all_command_ids(self):
        """Test get_targets includes all command IDs."""
        config = ClaudeSlashCommandConfigurator()
        targets = config.get_targets()

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)

    def test_get_targets_paths_match_get_relative_path(self):
        """Test that target paths match get_relative_path output."""
        config = ClaudeSlashCommandConfigurator()
        targets = config.get_targets()

        for target in targets:
            expected_path = config.get_relative_path(target.command_id)
            assert target.path == expected_path
