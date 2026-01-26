"""Parametrized tests for simple markdown-based slash command configurators.

Tests all 8 simple markdown tools that follow the standard pattern:
- Antigravity, Auggie, CodeBuddy, CoStrict, Crush, iFlow, Qoder, Qwen

These tools all use markdown files with YAML frontmatter (or toml for Qwen)
and follow the standard SlashCommandConfigurator interface.
"""

from pathlib import Path
from typing import Any

import pytest

from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.templates.slash_commands import get_command_body

# Tool configuration data for parametrized tests
# Each tool defines: tool_id, directory pattern, file naming, extension
SIMPLE_MARKDOWN_TOOLS = [
    pytest.param(
        "antigravity",
        ".agent/workflows",
        "aurora-{cmd}.md",
        {
            "plan": {"description": True},
            "query": {"description": True},
        },
        id="antigravity",
    ),
    pytest.param(
        "auggie",
        ".augment/commands",
        "aurora-{cmd}.md",
        {
            "plan": {"description": True, "argument-hint": True},
            "query": {"description": True, "argument-hint": True},
        },
        id="auggie",
    ),
    pytest.param(
        "codebuddy",
        ".codebuddy/commands/aurora",
        "{cmd}.md",
        {
            "plan": {"name": True, "description": True, "category": True, "tags": True},
            "query": {"name": True, "description": True, "category": True, "tags": True},
        },
        id="codebuddy",
    ),
    pytest.param(
        "costrict",
        ".cospec/aurora/commands",
        "aurora-{cmd}.md",
        {
            "plan": {"description": True, "argument-hint": True},
            "query": {"description": True, "argument-hint": True},
        },
        id="costrict",
    ),
    pytest.param(
        "crush",
        ".crush/commands/aurora",
        "{cmd}.md",
        {
            "plan": {"name": True, "description": True, "category": True, "tags": True},
            "query": {"name": True, "description": True, "category": True, "tags": True},
        },
        id="crush",
    ),
    pytest.param(
        "iflow",
        ".iflow/commands",
        "aurora-{cmd}.md",
        {
            "plan": {"name": True, "id": True, "category": True, "description": True},
            "query": {"name": True, "id": True, "category": True, "description": True},
        },
        id="iflow",
    ),
    pytest.param(
        "qoder",
        ".qoder/commands/aurora",
        "{cmd}.md",
        {
            "plan": {"name": True, "description": True, "category": True, "tags": True},
            "query": {"name": True, "description": True, "category": True, "tags": True},
        },
        id="qoder",
    ),
]

# Qwen uses TOML format, tested separately
QWEN_TOOL_CONFIG = pytest.param(
    "qwen",
    ".qwen/commands",
    "aurora-{cmd}.toml",
    {
        "plan": {"description": True},
        "query": {"description": True},
    },
    id="qwen",
)


def get_configurator(tool_id: str) -> SlashCommandConfigurator:
    """Import and instantiate a configurator by tool ID.

    This imports lazily to avoid import errors if a tool is not yet implemented.
    """
    if tool_id == "antigravity":
        from aurora_cli.configurators.slash.antigravity import AntigravitySlashCommandConfigurator

        return AntigravitySlashCommandConfigurator()
    if tool_id == "auggie":
        from aurora_cli.configurators.slash.auggie import AuggieSlashCommandConfigurator

        return AuggieSlashCommandConfigurator()
    if tool_id == "codebuddy":
        from aurora_cli.configurators.slash.codebuddy import CodeBuddySlashCommandConfigurator

        return CodeBuddySlashCommandConfigurator()
    if tool_id == "costrict":
        from aurora_cli.configurators.slash.costrict import CostrictSlashCommandConfigurator

        return CostrictSlashCommandConfigurator()
    if tool_id == "crush":
        from aurora_cli.configurators.slash.crush import CrushSlashCommandConfigurator

        return CrushSlashCommandConfigurator()
    if tool_id == "iflow":
        from aurora_cli.configurators.slash.iflow import IflowSlashCommandConfigurator

        return IflowSlashCommandConfigurator()
    if tool_id == "qoder":
        from aurora_cli.configurators.slash.qoder import QoderSlashCommandConfigurator

        return QoderSlashCommandConfigurator()
    if tool_id == "qwen":
        from aurora_cli.configurators.slash.qwen import QwenSlashCommandConfigurator

        return QwenSlashCommandConfigurator()
    raise ValueError(f"Unknown tool: {tool_id}")


class TestMarkdownToolProperties:
    """Tests for basic properties of markdown-based configurators."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_tool_id_property(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test that tool_id property returns correct value."""
        config = get_configurator(tool_id)
        assert config.tool_id == tool_id

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_is_available_property(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test that is_available property returns True."""
        config = get_configurator(tool_id)
        assert config.is_available is True

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_inherits_from_slash_command_configurator(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test that configurator inherits from SlashCommandConfigurator."""
        config = get_configurator(tool_id)
        assert isinstance(config, SlashCommandConfigurator)


class TestMarkdownToolPaths:
    """Tests for path-related methods."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_relative_path_returns_correct_directory(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test get_relative_path returns path in correct directory."""
        config = get_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(dir_pattern), f"Path {path} should start with {dir_pattern}"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_relative_path_has_md_extension(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test get_relative_path returns paths with .md extension."""
        config = get_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.endswith(".md"), f"Path {path} should end with .md"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_resolve_absolute_path(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test resolve_absolute_path returns absolute path."""
        config = get_configurator(tool_id)
        abs_path = config.resolve_absolute_path(str(tmp_path), "plan")

        assert Path(abs_path).is_absolute()
        expected = str(tmp_path / config.get_relative_path("plan"))
        assert abs_path == expected


class TestMarkdownToolFrontmatter:
    """Tests for frontmatter generation."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_frontmatter_returns_value(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test get_frontmatter returns a non-None value for all commands."""
        config = get_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            # Should return either None or a string (both are valid per the interface)
            assert frontmatter is None or isinstance(frontmatter, str)

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_frontmatter_has_yaml_delimiters_if_not_none(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test frontmatter has YAML delimiters if it's not None."""
        config = get_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            if frontmatter is not None:
                # Should have YAML delimiters (---) OR be a markdown header format
                has_yaml = frontmatter.startswith("---")
                has_markdown_header = frontmatter.startswith("#")
                assert (
                    has_yaml or has_markdown_header
                ), f"Frontmatter for {tool_id}/{cmd_id} should have YAML delimiters or markdown header"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_frontmatter_has_expected_fields(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test frontmatter contains expected fields for the tool."""
        config = get_configurator(tool_id)

        # Check a sample command (plan) for expected fields
        if "plan" in frontmatter_fields:
            frontmatter = config.get_frontmatter("plan")
            if frontmatter is not None and frontmatter.startswith("---"):
                expected = frontmatter_fields["plan"]
                for field, should_exist in expected.items():
                    if should_exist:
                        assert (
                            field in frontmatter.lower()
                            or field.replace("-", "") in frontmatter.lower()
                        ), f"Frontmatter for {tool_id}/plan should contain {field}"


class TestMarkdownToolBody:
    """Tests for body content generation."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_body_returns_template(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test get_body returns content from slash_commands templates."""
        config = get_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            body = config.get_body(cmd_id)
            expected = get_command_body(cmd_id)
            assert expected in body, f"Body for {tool_id}/{cmd_id} should contain template"


class TestMarkdownToolGenerateAll:
    """Tests for generate_all method."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_generate_all_creates_all_command_files(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generate_all creates files for all commands."""
        config = get_configurator(tool_id)
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            assert file_path.exists(), f"File for {tool_id}/{cmd_id} should exist"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_generate_all_files_have_aurora_markers(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generated files contain Aurora markers."""
        config = get_configurator(tool_id)
        config.generate_all(str(tmp_path), ".aurora")

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            content = file_path.read_text()

            assert (
                AURORA_MARKERS["start"] in content
            ), f"File for {tool_id}/{cmd_id} should have start marker"
            assert (
                AURORA_MARKERS["end"] in content
            ), f"File for {tool_id}/{cmd_id} should have end marker"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_generate_all_files_have_body_between_markers(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generated files have body content between markers."""
        config = get_configurator(tool_id)
        config.generate_all(str(tmp_path), ".aurora")

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            content = file_path.read_text()

            start_idx = content.find(AURORA_MARKERS["start"]) + len(AURORA_MARKERS["start"])
            end_idx = content.find(AURORA_MARKERS["end"])

            between_markers = content[start_idx:end_idx].strip()
            expected_body = get_command_body(cmd_id)

            assert (
                expected_body in between_markers or expected_body.strip() in between_markers
            ), f"File for {tool_id}/{cmd_id} should have body between markers"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_generate_all_returns_relative_paths(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generate_all returns relative paths."""
        config = get_configurator(tool_id)
        created = config.generate_all(str(tmp_path), ".aurora")

        for path in created:
            assert not Path(path).is_absolute(), f"Path {path} should be relative"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_generate_all_creates_directory_structure(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generate_all creates the directory structure."""
        config = get_configurator(tool_id)
        config.generate_all(str(tmp_path), ".aurora")

        # Check that directory exists
        expected_dir = tmp_path / dir_pattern
        assert expected_dir.exists(), f"Directory {dir_pattern} should exist"


class TestMarkdownToolUpdateExisting:
    """Tests for update_existing method."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_update_existing_only_updates_existing_files(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test update_existing does not create new files."""
        config = get_configurator(tool_id)

        # Create only one file manually
        plan_path = tmp_path / config.get_relative_path("plan")
        plan_path.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = config.get_frontmatter("plan")
        content = ""
        if frontmatter:
            content = f"{frontmatter}\n\n"
        content += f"{AURORA_MARKERS['start']}\nOld body\n{AURORA_MARKERS['end']}\n"
        plan_path.write_text(content)

        updated = config.update_existing(str(tmp_path), ".aurora")

        # Only one file should be updated
        assert len(updated) == 1

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_update_existing_replaces_body_between_markers(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test update_existing replaces body content between markers."""
        config = get_configurator(tool_id)

        # First generate all files
        config.generate_all(str(tmp_path), ".aurora")

        # Modify one file to have old content
        plan_path = tmp_path / config.get_relative_path("plan")
        original_content = plan_path.read_text()

        # Replace body with old content
        start_marker = AURORA_MARKERS["start"]
        end_marker = AURORA_MARKERS["end"]
        start_idx = original_content.find(start_marker) + len(start_marker)
        end_idx = original_content.find(end_marker)

        old_body = "\nThis is OLD body content.\n"
        modified_content = original_content[:start_idx] + old_body + original_content[end_idx:]
        plan_path.write_text(modified_content)

        # Verify old content is there
        assert "OLD body content" in plan_path.read_text()

        # Now update existing
        config.update_existing(str(tmp_path), ".aurora")

        # Old content should be gone, new content should be there
        updated_content = plan_path.read_text()
        assert "OLD body content" not in updated_content

        expected_body = get_command_body("plan")
        assert expected_body in updated_content or expected_body.strip() in updated_content


class TestMarkdownToolTargets:
    """Tests for get_targets method."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_targets_returns_all_commands(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test get_targets returns targets for all commands."""
        config = get_configurator(tool_id)
        targets = config.get_targets()

        assert len(targets) == len(ALL_COMMANDS)

        command_ids = {t.command_id for t in targets}
        assert command_ids == set(ALL_COMMANDS)

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_targets_returns_slash_command_targets(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test get_targets returns SlashCommandTarget objects."""
        config = get_configurator(tool_id)
        targets = config.get_targets()

        for target in targets:
            assert isinstance(target, SlashCommandTarget)
            assert target.kind == "slash"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,frontmatter_fields",
        SIMPLE_MARKDOWN_TOOLS,
    )
    def test_get_targets_paths_match_get_relative_path(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        frontmatter_fields: dict[str, Any],
    ) -> None:
        """Test that target paths match get_relative_path output."""
        config = get_configurator(tool_id)
        targets = config.get_targets()

        for target in targets:
            expected_path = config.get_relative_path(target.command_id)
            assert target.path == expected_path


# ============================================================================
# Tools with special frontmatter patterns
# ============================================================================

# These tools have unique frontmatter patterns:
# - Amazon Q: $ARGUMENTS placeholder and <UserRequest> tags
# - Cline: Markdown heading frontmatter (# Aurora: {Command})
# - RooCode: Markdown heading frontmatter (# Aurora: {Command})
# - Factory: Simple YAML with argument-hint and $ARGUMENTS in body
# - GitHub Copilot: Simple YAML with $ARGUMENTS placeholder
# - Kilo Code: No frontmatter (returns None)
# - OpenCode: $ARGUMENTS placeholder with <UserRequest> tags

SPECIAL_FRONTMATTER_TOOLS = [
    pytest.param(
        "amazon-q",
        ".amazonq/prompts",
        "aurora-{cmd}.md",
        {"$ARGUMENTS": True, "UserRequest": True},
        id="amazon-q",
    ),
    pytest.param(
        "cline",
        ".clinerules/workflows",
        "aurora-{cmd}.md",
        {"heading": True},  # Uses markdown heading format
        id="cline",
    ),
    pytest.param(
        "roocode",
        ".roo/commands",
        "aurora-{cmd}.md",
        {"heading": True},  # Uses markdown heading format
        id="roocode",
    ),
    pytest.param(
        "factory",
        ".factory/commands",
        "aurora-{cmd}.md",
        {"description": True, "argument-hint": True},
        id="factory",
    ),
    pytest.param(
        "github-copilot",
        ".github/prompts",
        "aurora-{cmd}.prompt.md",
        {"description": True, "$ARGUMENTS": True},
        id="github-copilot",
    ),
    pytest.param(
        "kilocode",
        ".kilocode/workflows",
        "aurora-{cmd}.md",
        {"none": True},  # No frontmatter
        id="kilocode",
    ),
    pytest.param(
        "opencode",
        ".opencode/command",
        "aurora-{cmd}.md",
        {"description": True, "$ARGUMENTS": True, "UserRequest": True},
        id="opencode",
    ),
]


def get_special_configurator(tool_id: str) -> SlashCommandConfigurator:
    """Import and instantiate a special configurator by tool ID.

    This imports lazily to avoid import errors if a tool is not yet implemented.
    """
    if tool_id == "amazon-q":
        from aurora_cli.configurators.slash.amazon_q import AmazonQSlashCommandConfigurator

        return AmazonQSlashCommandConfigurator()
    if tool_id == "cline":
        from aurora_cli.configurators.slash.cline import ClineSlashCommandConfigurator

        return ClineSlashCommandConfigurator()
    if tool_id == "roocode":
        from aurora_cli.configurators.slash.roocode import RooCodeSlashCommandConfigurator

        return RooCodeSlashCommandConfigurator()
    if tool_id == "factory":
        from aurora_cli.configurators.slash.factory import FactorySlashCommandConfigurator

        return FactorySlashCommandConfigurator()
    if tool_id == "github-copilot":
        from aurora_cli.configurators.slash.github_copilot import (
            GitHubCopilotSlashCommandConfigurator,
        )

        return GitHubCopilotSlashCommandConfigurator()
    if tool_id == "kilocode":
        from aurora_cli.configurators.slash.kilocode import KiloCodeSlashCommandConfigurator

        return KiloCodeSlashCommandConfigurator()
    if tool_id == "opencode":
        from aurora_cli.configurators.slash.opencode import OpenCodeSlashCommandConfigurator

        return OpenCodeSlashCommandConfigurator()
    raise ValueError(f"Unknown special tool: {tool_id}")


class TestSpecialFrontmatterToolProperties:
    """Tests for properties of tools with special frontmatter patterns."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_tool_id_property(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
    ) -> None:
        """Test that tool_id property returns correct value."""
        config = get_special_configurator(tool_id)
        assert config.tool_id == tool_id

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_is_available_property(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
    ) -> None:
        """Test that is_available property returns True."""
        config = get_special_configurator(tool_id)
        assert config.is_available is True

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_inherits_from_slash_command_configurator(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
    ) -> None:
        """Test that configurator inherits from SlashCommandConfigurator."""
        config = get_special_configurator(tool_id)
        assert isinstance(config, SlashCommandConfigurator)


class TestSpecialFrontmatterToolPaths:
    """Tests for path-related methods of special frontmatter tools."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_get_relative_path_returns_correct_directory(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
    ) -> None:
        """Test get_relative_path returns path in correct directory."""
        config = get_special_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.startswith(dir_pattern), f"Path {path} should start with {dir_pattern}"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_get_relative_path_has_md_extension(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
    ) -> None:
        """Test get_relative_path returns paths with .md extension."""
        config = get_special_configurator(tool_id)

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.endswith(".md"), f"Path {path} should end with .md"


class TestAmazonQSpecialFrontmatter:
    """Tests specific to Amazon Q's $ARGUMENTS and <UserRequest> patterns."""

    def test_frontmatter_contains_arguments_placeholder(self) -> None:
        """Test Amazon Q frontmatter contains $ARGUMENTS placeholder."""
        from aurora_cli.configurators.slash.amazon_q import AmazonQSlashCommandConfigurator

        config = AmazonQSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert "$ARGUMENTS" in frontmatter

    def test_frontmatter_contains_user_request_tags(self) -> None:
        """Test Amazon Q frontmatter contains <UserRequest> tags."""
        from aurora_cli.configurators.slash.amazon_q import AmazonQSlashCommandConfigurator

        config = AmazonQSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert "<UserRequest>" in frontmatter


class TestClineSpecialFrontmatter:
    """Tests specific to Cline's markdown heading frontmatter."""

    def test_frontmatter_is_markdown_heading(self) -> None:
        """Test Cline frontmatter is a markdown heading format."""
        from aurora_cli.configurators.slash.cline import ClineSlashCommandConfigurator

        config = ClineSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert frontmatter.startswith("# Aurora:")

    def test_frontmatter_contains_command_name(self) -> None:
        """Test Cline frontmatter contains the command name."""
        from aurora_cli.configurators.slash.cline import ClineSlashCommandConfigurator

        config = ClineSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        # Should contain "Plan" (capitalized)
        assert "Plan" in frontmatter

    def test_frontmatter_has_description_after_heading(self) -> None:
        """Test Cline frontmatter has description after the heading."""
        from aurora_cli.configurators.slash.cline import ClineSlashCommandConfigurator

        config = ClineSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        # Should have multiple lines with description
        lines = frontmatter.strip().split("\n")
        assert len(lines) >= 2


class TestRooCodeSpecialFrontmatter:
    """Tests specific to RooCode's markdown heading frontmatter."""

    def test_frontmatter_is_markdown_heading(self) -> None:
        """Test RooCode frontmatter is a markdown heading format."""
        from aurora_cli.configurators.slash.roocode import RooCodeSlashCommandConfigurator

        config = RooCodeSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert frontmatter.startswith("# Aurora:")

    def test_frontmatter_contains_command_name(self) -> None:
        """Test RooCode frontmatter contains the command name."""
        from aurora_cli.configurators.slash.roocode import RooCodeSlashCommandConfigurator

        config = RooCodeSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        # Should contain "Plan" (capitalized)
        assert "Plan" in frontmatter


class TestKiloCodeSpecialFrontmatter:
    """Tests specific to Kilo Code's no-frontmatter pattern."""

    def test_frontmatter_is_none(self) -> None:
        """Test Kilo Code returns None for frontmatter."""
        from aurora_cli.configurators.slash.kilocode import KiloCodeSlashCommandConfigurator

        config = KiloCodeSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            frontmatter = config.get_frontmatter(cmd_id)
            assert frontmatter is None


class TestGitHubCopilotSpecialFrontmatter:
    """Tests specific to GitHub Copilot's frontmatter patterns."""

    def test_frontmatter_contains_arguments_placeholder(self) -> None:
        """Test GitHub Copilot frontmatter contains $ARGUMENTS placeholder."""
        from aurora_cli.configurators.slash.github_copilot import (
            GitHubCopilotSlashCommandConfigurator,
        )

        config = GitHubCopilotSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert "$ARGUMENTS" in frontmatter

    def test_has_prompt_md_extension(self) -> None:
        """Test GitHub Copilot files have .prompt.md extension."""
        from aurora_cli.configurators.slash.github_copilot import (
            GitHubCopilotSlashCommandConfigurator,
        )

        config = GitHubCopilotSlashCommandConfigurator()

        for cmd_id in ALL_COMMANDS:
            path = config.get_relative_path(cmd_id)
            assert path.endswith(".prompt.md"), f"Path {path} should end with .prompt.md"


class TestOpenCodeSpecialFrontmatter:
    """Tests specific to OpenCode's frontmatter patterns."""

    def test_frontmatter_contains_arguments_placeholder(self) -> None:
        """Test OpenCode frontmatter contains $ARGUMENTS placeholder."""
        from aurora_cli.configurators.slash.opencode import OpenCodeSlashCommandConfigurator

        config = OpenCodeSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert "$ARGUMENTS" in frontmatter

    def test_frontmatter_contains_user_request_tags(self) -> None:
        """Test OpenCode frontmatter contains <UserRequest> tags."""
        from aurora_cli.configurators.slash.opencode import OpenCodeSlashCommandConfigurator

        config = OpenCodeSlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert "<UserRequest>" in frontmatter


class TestFactorySpecialFrontmatter:
    """Tests specific to Factory's frontmatter patterns."""

    def test_frontmatter_has_argument_hint(self) -> None:
        """Test Factory frontmatter has argument-hint field."""
        from aurora_cli.configurators.slash.factory import FactorySlashCommandConfigurator

        config = FactorySlashCommandConfigurator()

        frontmatter = config.get_frontmatter("plan")
        assert frontmatter is not None
        assert "argument-hint" in frontmatter

    def test_body_contains_arguments_placeholder(self) -> None:
        """Test Factory body contains $ARGUMENTS placeholder."""
        from aurora_cli.configurators.slash.factory import FactorySlashCommandConfigurator

        config = FactorySlashCommandConfigurator()

        body = config.get_body("plan")
        assert "$ARGUMENTS" in body


class TestSpecialFrontmatterToolGenerateAll:
    """Tests for generate_all method on special frontmatter tools."""

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_generate_all_creates_all_command_files(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generate_all creates files for all commands."""
        config = get_special_configurator(tool_id)
        created = config.generate_all(str(tmp_path), ".aurora")

        assert len(created) == len(ALL_COMMANDS)

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            assert file_path.exists(), f"File for {tool_id}/{cmd_id} should exist"

    @pytest.mark.parametrize(
        "tool_id,dir_pattern,file_pattern,special_fields",
        SPECIAL_FRONTMATTER_TOOLS,
    )
    def test_generate_all_files_have_aurora_markers(
        self,
        tool_id: str,
        dir_pattern: str,
        file_pattern: str,
        special_fields: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generated files contain Aurora markers."""
        config = get_special_configurator(tool_id)
        config.generate_all(str(tmp_path), ".aurora")

        for cmd_id in ALL_COMMANDS:
            file_path = tmp_path / config.get_relative_path(cmd_id)
            content = file_path.read_text()

            assert (
                AURORA_MARKERS["start"] in content
            ), f"File for {tool_id}/{cmd_id} should have start marker"
            assert (
                AURORA_MARKERS["end"] in content
            ), f"File for {tool_id}/{cmd_id} should have end marker"
