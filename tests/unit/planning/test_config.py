"""Tests for config module."""

import pytest

from aurora_planning.config import (
    AI_TOOLS,
    AURORA_DIR_NAME,
    AURORA_MARKERS,
    AIToolOption,
    AuroraConfig,
)


class TestConstants:
    """Tests for configuration constants."""

    def test_aurora_dir_name(self):
        """Test AURORA_DIR_NAME constant."""
        assert AURORA_DIR_NAME == "aurora"

    def test_aurora_markers(self):
        """Test AURORA_MARKERS dictionary."""
        assert "start" in AURORA_MARKERS
        assert "end" in AURORA_MARKERS
        assert AURORA_MARKERS["start"] == "<!-- AURORA:START -->"
        assert AURORA_MARKERS["end"] == "<!-- AURORA:END -->"


class TestAIToolOption:
    """Tests for AIToolOption dataclass."""

    def test_creates_tool_option(self):
        """Test creating an AIToolOption."""
        tool = AIToolOption("Test Tool", "test-tool", True, "Test Tool")
        assert tool.name == "Test Tool"
        assert tool.value == "test-tool"
        assert tool.available is True
        assert tool.success_label == "Test Tool"

    def test_tool_option_without_success_label(self):
        """Test creating tool option without success label."""
        tool = AIToolOption("Test Tool", "test-tool", False)
        assert tool.success_label is None


class TestAITools:
    """Tests for AI_TOOLS list."""

    def test_ai_tools_is_list(self):
        """Test AI_TOOLS is a list."""
        assert isinstance(AI_TOOLS, list)

    def test_ai_tools_not_empty(self):
        """Test AI_TOOLS contains items."""
        assert len(AI_TOOLS) > 0

    def test_all_items_are_ai_tool_options(self):
        """Test all items in AI_TOOLS are AIToolOption instances."""
        for tool in AI_TOOLS:
            assert isinstance(tool, AIToolOption)

    def test_claude_code_in_tools(self):
        """Test Claude Code is in the tools list."""
        claude_tools = [t for t in AI_TOOLS if t.value == "claude"]
        assert len(claude_tools) == 1
        assert claude_tools[0].name == "Claude Code"


class TestAuroraConfig:
    """Tests for AuroraConfig dataclass."""

    def test_creates_aurora_config(self):
        """Test creating an AuroraConfig."""
        config = AuroraConfig(ai_tools=["claude", "cursor"])
        assert config.ai_tools == ["claude", "cursor"]

    def test_empty_ai_tools(self):
        """Test creating config with empty AI tools list."""
        config = AuroraConfig(ai_tools=[])
        assert config.ai_tools == []
