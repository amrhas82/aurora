"""Tests for AI_TOOLS configuration constant.

This test module verifies that the AI_TOOLS configuration constant is properly
defined with all 20 AI coding tools and required metadata.

Test-Driven Development (TDD):
- These tests are written FIRST (RED phase)
- Implementation in config.py comes SECOND (GREEN phase)
"""

import pytest


class TestAIToolsConstant:
    """Test AI_TOOLS configuration constant structure and content."""

    def test_ai_tools_is_list_of_20_dicts(self):
        """AI_TOOLS should be a list of exactly 20 dictionaries."""
        from aurora_cli.config import AI_TOOLS

        assert isinstance(AI_TOOLS, list), "AI_TOOLS should be a list"
        assert len(AI_TOOLS) == 20, f"AI_TOOLS should have 20 tools, got {len(AI_TOOLS)}"

        for i, tool in enumerate(AI_TOOLS):
            assert isinstance(tool, dict), f"AI_TOOLS[{i}] should be a dict"

    def test_each_tool_has_required_keys(self):
        """Each tool dict should have name, value, and available keys."""
        from aurora_cli.config import AI_TOOLS

        required_keys = {"name", "value", "available"}

        for i, tool in enumerate(AI_TOOLS):
            for key in required_keys:
                assert key in tool, f"AI_TOOLS[{i}] missing required key '{key}'"

    def test_tool_value_matches_registry_tool_ids(self):
        """Tool 'value' field should match SlashCommandRegistry tool IDs."""
        from aurora_cli.config import AI_TOOLS
        from aurora_cli.configurators.slash import SlashCommandRegistry

        registry_tool_ids = {c.tool_id for c in SlashCommandRegistry.get_all()}

        for tool in AI_TOOLS:
            assert tool["value"] in registry_tool_ids, (
                f"Tool value '{tool['value']}' not found in SlashCommandRegistry"
            )

    def test_all_tools_have_available_true(self):
        """All tools should have available: True (all are always available per PRD)."""
        from aurora_cli.config import AI_TOOLS

        for tool in AI_TOOLS:
            assert tool["available"] is True, (
                f"Tool '{tool['value']}' should have available=True"
            )

    def test_tool_name_is_non_empty_string(self):
        """Tool 'name' field should be a non-empty string."""
        from aurora_cli.config import AI_TOOLS

        for tool in AI_TOOLS:
            assert isinstance(tool["name"], str), f"Tool '{tool['value']}' name should be str"
            assert len(tool["name"]) > 0, f"Tool '{tool['value']}' name should not be empty"

    def test_tool_value_is_non_empty_string(self):
        """Tool 'value' field should be a non-empty string (the tool_id)."""
        from aurora_cli.config import AI_TOOLS

        for tool in AI_TOOLS:
            assert isinstance(tool["value"], str), f"Tool value should be str"
            assert len(tool["value"]) > 0, f"Tool value should not be empty"

    def test_all_20_expected_tools_present(self):
        """AI_TOOLS should include all 20 expected AI coding tools."""
        from aurora_cli.config import AI_TOOLS

        expected_tool_ids = {
            "amazon-q",
            "antigravity",
            "auggie",
            "claude",
            "cline",
            "codex",
            "codebuddy",
            "costrict",
            "crush",
            "cursor",
            "factory",
            "gemini",
            "github-copilot",
            "iflow",
            "kilocode",
            "opencode",
            "qoder",
            "qwen",
            "roocode",
            "windsurf",
        }

        actual_tool_ids = {tool["value"] for tool in AI_TOOLS}

        assert expected_tool_ids == actual_tool_ids, (
            f"Missing tools: {expected_tool_ids - actual_tool_ids}\n"
            f"Unexpected tools: {actual_tool_ids - expected_tool_ids}"
        )

    def test_tool_names_are_human_readable(self):
        """Tool names should be human-readable display names (not just IDs)."""
        from aurora_cli.config import AI_TOOLS

        # These tools have specific human-readable names
        expected_names = {
            "amazon-q": "Amazon Q",
            "claude": "Claude Code",
            "github-copilot": "GitHub Copilot",
            "gemini": "Gemini CLI",
        }

        for tool in AI_TOOLS:
            tool_id = tool["value"]
            if tool_id in expected_names:
                assert tool["name"] == expected_names[tool_id], (
                    f"Tool '{tool_id}' should have name '{expected_names[tool_id]}', "
                    f"got '{tool['name']}'"
                )

    def test_ai_tools_can_be_imported_from_config(self):
        """AI_TOOLS should be importable from aurora_cli.config."""
        try:
            from aurora_cli.config import AI_TOOLS
            assert AI_TOOLS is not None
        except ImportError as e:
            pytest.fail(f"Failed to import AI_TOOLS: {e}")

    def test_no_duplicate_tool_ids(self):
        """AI_TOOLS should not have duplicate tool IDs (values)."""
        from aurora_cli.config import AI_TOOLS

        tool_ids = [tool["value"] for tool in AI_TOOLS]
        assert len(tool_ids) == len(set(tool_ids)), "AI_TOOLS contains duplicate tool IDs"

    def test_no_duplicate_tool_names(self):
        """AI_TOOLS should not have duplicate tool names."""
        from aurora_cli.config import AI_TOOLS

        tool_names = [tool["name"] for tool in AI_TOOLS]
        assert len(tool_names) == len(set(tool_names)), "AI_TOOLS contains duplicate tool names"
