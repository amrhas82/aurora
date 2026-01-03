"""Tests for tool configurators."""

import pytest
from pathlib import Path

from aurora_cli.configurators import (
    ToolRegistry,
    ClaudeConfigurator,
    OpenCodeConfigurator,
    AmpCodeConfigurator,
    DroidConfigurator,
    AgentsStandardConfigurator,
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

        assert ".aurora/plans/" in content
        assert "aur plan create" in content
        assert "aur plan list" in content
        assert "CLAUDE.md" not in content  # Shouldn't self-reference

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
        assert ".aurora/plans/" in content

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
        assert ".aurora/plans/" in updated


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

        assert ".aurora/plans/" in content
        assert "aur plan" in content


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

        assert ".aurora/plans/" in content
        assert "aur plan" in content


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

        assert ".aurora/plans/" in content
        assert "aur plan" in content


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

        assert ".aurora/plans/" in content
        assert "aur plan" in content
        assert "AGENTS.md" not in content  # Shouldn't self-reference in instructions

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
        assert "Aurora Planning System" in content
