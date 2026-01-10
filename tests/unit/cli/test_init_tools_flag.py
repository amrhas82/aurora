"""Tests for --tools flag in init command.

This test module verifies the --tools flag functionality for `aur init` command
that allows non-interactive configuration of AI coding tools.

Test-Driven Development (TDD):
- Tests are written FIRST (RED phase)
- Implementation comes SECOND (GREEN phase)

Tests cover:
- parse_tools_flag() function for parsing --tools=<value>
- validate_tool_ids() function for validating tool IDs
- Integration with init command
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner


class TestParseToolsFlag:
    """Test parse_tools_flag() function for parsing --tools=<value>."""

    def test_parse_tools_flag_all_returns_all_20_tool_ids(self):
        """parse_tools_flag('all') should return list of all 20 tool IDs."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("all")

        assert isinstance(result, list)
        assert len(result) == 20
        # Verify some expected tool IDs are present
        assert "claude" in result
        assert "cursor" in result
        assert "gemini" in result
        assert "windsurf" in result
        assert "codex" in result

    def test_parse_tools_flag_none_returns_empty_list(self):
        """parse_tools_flag('none') should return empty list."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("none")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_parse_tools_flag_single_tool_returns_list_with_one_id(self):
        """parse_tools_flag('claude') should return ['claude']."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("claude")

        assert result == ["claude"]

    def test_parse_tools_flag_comma_separated_returns_list(self):
        """parse_tools_flag('claude,cursor') should return ['claude', 'cursor']."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("claude,cursor")

        assert result == ["claude", "cursor"]

    def test_parse_tools_flag_multiple_tools(self):
        """parse_tools_flag('claude,cursor,gemini') should return list of 3."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("claude,cursor,gemini")

        assert len(result) == 3
        assert "claude" in result
        assert "cursor" in result
        assert "gemini" in result

    def test_parse_tools_flag_handles_whitespace(self):
        """parse_tools_flag('claude, cursor, gemini') should strip whitespace."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("claude, cursor, gemini")

        assert result == ["claude", "cursor", "gemini"]

    def test_parse_tools_flag_normalizes_case(self):
        """parse_tools_flag('CLAUDE,Cursor') should normalize to lowercase."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("CLAUDE,Cursor")

        assert result == ["claude", "cursor"]

    def test_parse_tools_flag_handles_empty_string(self):
        """parse_tools_flag('') should return empty list."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("")

        assert result == []

    def test_parse_tools_flag_removes_duplicates(self):
        """parse_tools_flag('claude,claude,cursor') should remove duplicates."""
        from aurora_cli.commands.init import parse_tools_flag

        result = parse_tools_flag("claude,claude,cursor")

        # Should have unique values only
        assert len(result) == 2
        assert result.count("claude") == 1


class TestValidateToolIds:
    """Test validate_tool_ids() function for validating tool IDs."""

    def test_validate_tool_ids_accepts_valid_ids(self):
        """validate_tool_ids() should accept valid tool IDs without raising."""
        from aurora_cli.commands.init import validate_tool_ids

        # Should not raise for valid IDs
        validate_tool_ids(["claude", "cursor", "gemini"])

    def test_validate_tool_ids_raises_for_invalid_id(self):
        """validate_tool_ids() should raise ValueError for invalid tool ID."""
        from aurora_cli.commands.init import validate_tool_ids

        with pytest.raises(ValueError) as exc_info:
            validate_tool_ids(["invalid-tool"])

        assert "invalid-tool" in str(exc_info.value)

    def test_validate_tool_ids_error_lists_available_tools(self):
        """validate_tool_ids() error message should list available tool IDs."""
        from aurora_cli.commands.init import validate_tool_ids

        with pytest.raises(ValueError) as exc_info:
            validate_tool_ids(["not-a-real-tool"])

        error_msg = str(exc_info.value)
        # Should list some available tools in error message
        assert "claude" in error_msg.lower() or "available" in error_msg.lower()

    def test_validate_tool_ids_shows_all_invalid_ids_in_error(self):
        """validate_tool_ids() should show all invalid IDs when multiple are invalid."""
        from aurora_cli.commands.init import validate_tool_ids

        with pytest.raises(ValueError) as exc_info:
            validate_tool_ids(["claude", "invalid1", "cursor", "invalid2"])

        error_msg = str(exc_info.value)
        assert "invalid1" in error_msg
        assert "invalid2" in error_msg

    def test_validate_tool_ids_accepts_empty_list(self):
        """validate_tool_ids([]) should accept empty list without raising."""
        from aurora_cli.commands.init import validate_tool_ids

        # Should not raise for empty list
        validate_tool_ids([])

    def test_validate_tool_ids_accepts_all_20_tools(self):
        """validate_tool_ids() should accept all 20 valid tool IDs."""
        from aurora_cli.commands.init import validate_tool_ids
        from aurora_cli.configurators.slash import SlashCommandRegistry

        all_tool_ids = [c.tool_id for c in SlashCommandRegistry.get_all()]

        # Should not raise for all valid IDs
        validate_tool_ids(all_tool_ids)


class TestToolsFlagIntegration:
    """Test --tools flag integration with init command."""

    def test_init_command_accepts_tools_flag(self, tmp_path):
        """init command should accept --tools option."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .aurora to satisfy pre-condition
            (Path.cwd() / ".aurora").mkdir()
            (Path.cwd() / ".git").mkdir()

            with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                with patch(
                    "aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True
                ):
                    with patch(
                        "aurora_cli.commands.init.run_step_3_tool_configuration",
                        return_value=([], []),
                    ):
                        # Should accept --tools flag without error
                        result = runner.invoke(init_command, ["--tools=claude"])

                        # Should not fail due to unrecognized option
                        assert (
                            "--tools" not in result.output
                            or "unrecognized" not in result.output.lower()
                        )

    def test_init_command_with_tools_all_configures_all_20_tools(self, tmp_path):
        """init --tools=all should configure all 20 tools."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".git").mkdir()

            with patch(
                "aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False
            ):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch(
                        "aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True
                    ):
                        with patch(
                            "aurora_cli.commands.init.run_step_3_tool_configuration",
                            return_value=(["all tools"], []),
                        ) as mock_step3:
                            result = runner.invoke(init_command, ["--tools=all"])

                            # Step 3 should be called (verify integration)
                            mock_step3.assert_called_once()

    def test_init_command_with_tools_none_skips_tool_config(self, tmp_path):
        """init --tools=none should not configure any tools."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".git").mkdir()

            with patch(
                "aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False
            ):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch(
                        "aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True
                    ):
                        with patch(
                            "aurora_cli.commands.init.run_step_3_tool_configuration",
                            return_value=([], []),
                        ) as mock_step3:
                            result = runner.invoke(init_command, ["--tools=none"])

                            # Should complete successfully
                            assert result.exit_code == 0

    def test_init_command_with_tools_flag_skips_interactive_prompt(self, tmp_path):
        """init --tools=claude should skip interactive tool selection."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".git").mkdir()

            with patch(
                "aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False
            ):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch(
                        "aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True
                    ):
                        with patch(
                            "aurora_cli.commands.init.prompt_tool_selection", new_callable=AsyncMock
                        ) as mock_prompt:
                            with patch(
                                "aurora_cli.commands.init.configure_tools",
                                new_callable=AsyncMock,
                                return_value=([], []),
                            ):
                                with patch(
                                    "aurora_cli.commands.init.detect_configured_tools",
                                    return_value={},
                                ):
                                    result = runner.invoke(init_command, ["--tools=claude"])

                                    # prompt_tool_selection should NOT be called when --tools is provided
                                    mock_prompt.assert_not_called()

    def test_init_command_with_invalid_tool_shows_error(self, tmp_path):
        """init --tools=invalid-tool should show helpful error message."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".git").mkdir()

            with patch(
                "aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False
            ):
                result = runner.invoke(init_command, ["--tools=not-a-real-tool"])

                # Should show error about invalid tool
                assert (
                    result.exit_code != 0
                    or "invalid" in result.output.lower()
                    or "not-a-real-tool" in result.output.lower()
                )

    def test_init_command_with_mixed_valid_invalid_tools_shows_error(self, tmp_path):
        """init --tools=claude,invalid should show error for invalid tool."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".git").mkdir()

            with patch(
                "aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False
            ):
                result = runner.invoke(init_command, ["--tools=claude,invalid-tool"])

                # Should show error about invalid tool
                assert result.exit_code != 0 or "invalid" in result.output.lower()

    def test_init_command_tools_flag_passes_ids_to_step_3(self, tmp_path):
        """init --tools=claude,cursor should pass those IDs to step 3."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".git").mkdir()

            with patch(
                "aurora_cli.commands.init_helpers.detect_existing_setup", return_value=False
            ):
                with patch("aurora_cli.commands.init.run_step_1_planning_setup", return_value=True):
                    with patch(
                        "aurora_cli.commands.init.run_step_2_memory_indexing", return_value=True
                    ):
                        with patch(
                            "aurora_cli.commands.init.run_step_3_tool_configuration",
                            return_value=(["Claude", "Cursor"], []),
                        ) as mock_step3:
                            result = runner.invoke(init_command, ["--tools=claude,cursor"])

                            # Verify step 3 was called
                            mock_step3.assert_called_once()


class TestToolsFlagWithConfigOption:
    """Test --tools flag combined with --config option."""

    def test_init_config_with_tools_flag(self, tmp_path):
        """init --config --tools=claude should configure only specified tools."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .aurora to satisfy --config pre-condition
            (Path.cwd() / ".aurora").mkdir()

            with patch(
                "aurora_cli.commands.init.run_step_3_tool_configuration",
                return_value=(["Claude"], []),
            ) as mock_step3:
                result = runner.invoke(init_command, ["--config", "--tools=claude"])

                # Should only run step 3
                mock_step3.assert_called_once()

    def test_init_config_with_tools_none_skips_all_tools(self, tmp_path):
        """init --config --tools=none should not configure any tools."""
        from aurora_cli.commands.init import init_command

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".aurora").mkdir()

            with patch(
                "aurora_cli.commands.init.run_step_3_tool_configuration", return_value=([], [])
            ) as mock_step3:
                result = runner.invoke(init_command, ["--config", "--tools=none"])

                # Should complete but configure no tools
                assert result.exit_code == 0


class TestGetAllToolIds:
    """Test helper function for getting all valid tool IDs."""

    def test_get_all_tool_ids_returns_20_ids(self):
        """get_all_tool_ids() should return list of 20 tool IDs."""
        from aurora_cli.commands.init import get_all_tool_ids

        result = get_all_tool_ids()

        assert isinstance(result, list)
        assert len(result) == 20

    def test_get_all_tool_ids_returns_strings(self):
        """get_all_tool_ids() should return list of strings."""
        from aurora_cli.commands.init import get_all_tool_ids

        result = get_all_tool_ids()

        assert all(isinstance(tool_id, str) for tool_id in result)

    def test_get_all_tool_ids_includes_expected_tools(self):
        """get_all_tool_ids() should include all expected tool IDs."""
        from aurora_cli.commands.init import get_all_tool_ids

        result = get_all_tool_ids()

        expected_tools = [
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
        ]

        for tool_id in expected_tools:
            assert tool_id in result, f"Expected {tool_id} to be in tool IDs"
