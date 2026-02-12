"""Tests for tool configurators."""

from pathlib import Path

import pytest

from aurora_cli.configurators import (
    AgentsStandardConfigurator,
    AmpCodeConfigurator,
    ClaudeConfigurator,
    DroidConfigurator,
    OpenCodeConfigurator,
    ToolRegistry,
)


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_get_all_returns_all_configurators(self):
        """Test that get_all returns all registered configurators."""
        tools = ToolRegistry.get_all()
        assert len(tools) >= 5  # At least our 5 core tools

        tool_names = {tool.name for tool in tools}
        expected_names = {
            "Claude Code",
            "OpenCode",
            "AmpCode",
            "Droid",
            "Universal AGENTS.md",
        }
        assert expected_names.issubset(tool_names)

    def test_get_available_returns_only_available(self):
        """Test that get_available returns only available configurators."""
        available = ToolRegistry.get_available()
        assert all(tool.is_available for tool in available)

    def test_get_by_id_claude(self):
        """Test getting Claude configurator by ID."""
        tool = ToolRegistry.get("claude-code")
        assert tool is not None
        assert tool.name == "Claude Code"
        assert tool.config_file_name == "CLAUDE.md"

    def test_get_by_id_opencode(self):
        """Test getting OpenCode configurator by ID."""
        tool = ToolRegistry.get("opencode")
        assert tool is not None
        assert tool.name == "OpenCode"

    def test_get_by_id_ampcode(self):
        """Test getting AmpCode configurator by ID."""
        tool = ToolRegistry.get("ampcode")
        assert tool is not None
        assert tool.name == "AmpCode"

    def test_get_by_id_droid(self):
        """Test getting Droid configurator by ID."""
        tool = ToolRegistry.get("droid")
        assert tool is not None
        assert tool.name == "Droid"

    def test_get_by_id_invalid_returns_none(self):
        """Test that invalid tool ID returns None."""
        tool = ToolRegistry.get("nonexistent-tool")
        assert tool is None

    def test_register_new_configurator(self):
        """Test registering a custom configurator."""

        class CustomConfigurator:
            name = "Custom Tool"
            config_file_name = "CUSTOM.md"
            is_available = True

            async def configure(self, project_path, aurora_dir):
                pass

        custom = CustomConfigurator()
        ToolRegistry.register(custom)

        retrieved = ToolRegistry.get("custom-tool")
        assert retrieved is not None
        assert retrieved.name == "Custom Tool"


class TestClaudeConfigurator:
    """Tests for ClaudeConfigurator."""

    def test_properties(self):
        """Test configurator properties."""
        config = ClaudeConfigurator()
        assert config.name == "Claude Code"
        assert config.config_file_name == "CLAUDE.md"
        assert config.is_available is True

    @pytest.mark.asyncio
    async def test_get_template_content(self):
        """Test template content generation."""
        config = ClaudeConfigurator()
        content = await config.get_template_content(".aurora")

        # Stub template references AGENTS.md and key concepts
        assert ".aurora/AGENTS.md" in content
        assert "Aurora Instructions" in content
        assert "aur init --config" in content

    @pytest.mark.asyncio
    async def test_configure_creates_file(self, tmp_path: Path):
        """Test that configure creates CLAUDE.md file."""
        config = ClaudeConfigurator()
        await config.configure(tmp_path, ".aurora")

        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()

        content = claude_md.read_text()
        assert "<!-- AURORA:START -->" in content
        assert "<!-- AURORA:END -->" in content
        assert ".aurora/AGENTS.md" in content

    @pytest.mark.asyncio
    async def test_configure_creates_slash_commands(self, tmp_path: Path):
        """Test that configure creates slash command files."""
        config = ClaudeConfigurator()
        await config.configure(tmp_path, ".aurora")

        # Check that slash command directory was created
        commands_dir = tmp_path / ".claude" / "commands" / "aur"
        assert commands_dir.exists()

        # Check that standardized command files exist (plan, checkpoint, archive)
        expected_commands = ["plan.md", "checkpoint.md", "archive.md"]
        for cmd in expected_commands:
            cmd_file = commands_dir / cmd
            assert cmd_file.exists(), f"Expected {cmd} to exist"
            content = cmd_file.read_text()
            assert "<!-- AURORA:START -->" in content

    @pytest.mark.asyncio
    async def test_configure_updates_existing_file(self, tmp_path: Path):
        """Test that configure updates existing file with markers."""
        claude_md = tmp_path / "CLAUDE.md"

        # Create existing file with markers
        existing_content = """# My Custom Header

<!-- AURORA:START -->
Old Aurora content
<!-- AURORA:END -->

# My Custom Footer
"""
        claude_md.write_text(existing_content)

        config = ClaudeConfigurator()
        await config.configure(tmp_path, ".aurora")

        # Check that custom content is preserved
        updated = claude_md.read_text()
        assert "# My Custom Header" in updated
        assert "# My Custom Footer" in updated
        assert "Old Aurora content" not in updated
        assert ".aurora/AGENTS.md" in updated


class TestOpenCodeConfigurator:
    """Tests for OpenCodeConfigurator."""

    def test_properties(self):
        """Test configurator properties."""
        config = OpenCodeConfigurator()
        assert config.name == "OpenCode"
        assert config.config_file_name == "OPENCODE.md"
        assert config.is_available is True

    @pytest.mark.asyncio
    async def test_get_template_content(self):
        """Test template content generation."""
        config = OpenCodeConfigurator()
        content = await config.get_template_content(".aurora")

        # Stub template references AGENTS.md
        assert ".aurora/AGENTS.md" in content
        assert "Aurora Instructions" in content


class TestAmpCodeConfigurator:
    """Tests for AmpCodeConfigurator."""

    def test_properties(self):
        """Test configurator properties."""
        config = AmpCodeConfigurator()
        assert config.name == "AmpCode"
        assert config.config_file_name == "AMPCODE.md"
        assert config.is_available is True

    @pytest.mark.asyncio
    async def test_get_template_content(self):
        """Test template content generation."""
        config = AmpCodeConfigurator()
        content = await config.get_template_content(".aurora")

        # Stub template references AGENTS.md
        assert ".aurora/AGENTS.md" in content
        assert "Aurora Instructions" in content


class TestDroidConfigurator:
    """Tests for DroidConfigurator."""

    def test_properties(self):
        """Test configurator properties."""
        config = DroidConfigurator()
        assert config.name == "Droid"
        assert config.config_file_name == "DROID.md"
        assert config.is_available is True

    @pytest.mark.asyncio
    async def test_get_template_content(self):
        """Test template content generation."""
        config = DroidConfigurator()
        content = await config.get_template_content(".aurora")

        # Stub template references AGENTS.md
        assert ".aurora/AGENTS.md" in content
        assert "Aurora Instructions" in content


class TestAgentsStandardConfigurator:
    """Tests for AgentsStandardConfigurator."""

    def test_properties(self):
        """Test configurator properties."""
        config = AgentsStandardConfigurator()
        assert config.name == "Universal AGENTS.md"
        assert config.config_file_name == "AGENTS.md"
        assert config.is_available is True

    @pytest.mark.asyncio
    async def test_get_template_content(self):
        """Test template content generation."""
        config = AgentsStandardConfigurator()
        content = await config.get_template_content(".aurora")

        # Full template has plan paths and command references
        assert ".aurora/plans/" in content
        assert "Aurora Instructions" in content

    @pytest.mark.asyncio
    async def test_configure_creates_root_agents_md(self, tmp_path: Path):
        """Test that configure creates root AGENTS.md file."""
        config = AgentsStandardConfigurator()
        await config.configure(tmp_path, ".aurora")

        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()

        content = agents_md.read_text()
        assert "<!-- AURORA:START -->" in content
        assert "<!-- AURORA:END -->" in content
        # Comprehensive template has Aurora header
        assert "Aurora" in content


class TestClaudeCommandsConfigurator:
    """Tests for ClaudeCommandsConfigurator."""

    def test_properties(self):
        """Test configurator properties."""
        from aurora_cli.configurators import ClaudeCommandsConfigurator

        config = ClaudeCommandsConfigurator()
        assert config.name == "Claude Commands"
        assert config.config_file_name == ".claude/commands/aur"
        assert config.is_available is True

    def test_get_command_list(self):
        """Test getting list of available commands."""
        from aurora_cli.configurators import ClaudeCommandsConfigurator

        config = ClaudeCommandsConfigurator()
        commands = config.get_command_list()

        # After standardization: plan, checkpoint, archive
        expected = ["plan", "checkpoint", "archive"]
        for cmd in expected:
            assert cmd in commands

    @pytest.mark.asyncio
    async def test_configure_creates_command_files(self, tmp_path: Path):
        """Test that configure creates all command files."""
        from aurora_cli.configurators import ClaudeCommandsConfigurator

        config = ClaudeCommandsConfigurator()
        created_files = await config.configure(tmp_path, ".aurora")

        # Check that files were created
        commands_dir = tmp_path / ".claude" / "commands" / "aur"
        assert commands_dir.exists()

        # Check each file
        for filename in created_files:
            file_path = commands_dir / filename
            assert file_path.exists()

            content = file_path.read_text()
            assert "---" in content  # Frontmatter
            assert "<!-- AURORA:START -->" in content
            assert "<!-- AURORA:END -->" in content

    @pytest.mark.asyncio
    async def test_configure_updates_existing_command(self, tmp_path: Path):
        """Test that configure updates existing command file."""
        from aurora_cli.configurators import ClaudeCommandsConfigurator

        # Create existing command file (using plan.md which now exists)
        commands_dir = tmp_path / ".claude" / "commands" / "aur"
        commands_dir.mkdir(parents=True, exist_ok=True)

        plan_file = commands_dir / "plan.md"
        plan_file.write_text(
            """---
name: Custom Plan
description: My custom description
---
<!-- AURORA:START -->
Old content
<!-- AURORA:END -->
""",
        )

        config = ClaudeCommandsConfigurator()
        await config.configure(tmp_path, ".aurora")

        # Check that file was updated
        updated = plan_file.read_text()
        assert "Aurora Plan" in updated  # New name from template
        assert "Old content" not in updated
