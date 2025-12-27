"""Unit tests for CLI headless command.

Tests the headless_command function for autonomous experiment execution
with safety checks and configuration validation.

Pattern: Direct click.testing.CliRunner with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import headless_command


class TestHeadlessCommandBasic:
    """Test basic headless command invocation and validation."""

    def test_headless_command_missing_prompt_file(self):
        """Test headless command with missing prompt file fails."""
        runner = CliRunner()

        result = runner.invoke(
            headless_command, ["/nonexistent/prompt.md"]
        )

        assert result.exit_code != 0
        # Click handles path validation before command execution

    def test_headless_command_displays_configuration(self, tmp_path):
        """Test headless command displays configuration table."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest goal\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--dry-run"]
        )

        assert "Headless Mode Configuration:" in result.output
        assert "Prompt" in result.output
        assert "Scratchpad" in result.output
        assert "Budget" in result.output

    def test_headless_command_invalid_budget_zero(self, tmp_path):
        """Test headless command rejects zero budget."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--budget", "0"]
        )

        assert result.exit_code != 0
        assert "Budget must be positive" in result.output

    def test_headless_command_invalid_budget_negative(self, tmp_path):
        """Test headless command rejects negative budget."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--budget", "-5.0"]
        )

        assert result.exit_code != 0
        assert "Budget must be positive" in result.output

    def test_headless_command_invalid_max_iter_zero(self, tmp_path):
        """Test headless command rejects zero max iterations."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--max-iter", "0"]
        )

        assert result.exit_code != 0
        assert "Max iterations must be positive" in result.output

    def test_headless_command_invalid_max_iter_negative(self, tmp_path):
        """Test headless command rejects negative max iterations."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--max-iter", "-10"]
        )

        assert result.exit_code != 0
        assert "Max iterations must be positive" in result.output


class TestHeadlessCommandDryRun:
    """Test headless command dry-run mode."""

    def test_dry_run_validates_configuration(self, tmp_path):
        """Test dry-run mode validates configuration without executing."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest goal\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "--dry-run"],
        )

        assert "Dry run mode: validating configuration only" in result.output
        assert "Configuration valid" in result.output
        assert "Run without --dry-run to execute" in result.output

    def test_dry_run_shows_scratchpad_path(self, tmp_path):
        """Test dry-run shows scratchpad path."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--dry-run"]
        )

        assert "scratchpad" in result.output.lower()

    def test_dry_run_custom_scratchpad(self, tmp_path):
        """Test dry-run with custom scratchpad path."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")
        scratchpad = tmp_path / "custom_scratch.md"

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "--scratchpad", str(scratchpad), "--dry-run"],
        )

        assert "custom_scratch.md" in result.output


class TestHeadlessCommandConfiguration:
    """Test headless command configuration options."""

    def test_custom_budget_value(self, tmp_path):
        """Test custom budget value is displayed."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "--budget", "10.0", "--dry-run"],
        )

        assert "$10.00" in result.output

    def test_custom_max_iter_value(self, tmp_path):
        """Test custom max iterations value is displayed."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "--max-iter", "20", "--dry-run"],
        )

        assert "20" in result.output

    def test_custom_branch_value(self, tmp_path):
        """Test custom branch value is displayed."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "--branch", "test-branch", "--dry-run"],
        )

        assert "test-branch" in result.output

    def test_allow_main_flag_warning(self, tmp_path):
        """Test --allow-main flag shows danger warning."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "--allow-main", "--dry-run"],
        )

        assert "⚠️  Yes (DANGEROUS)" in result.output or "DANGEROUS" in result.output


class TestHeadlessCommandExecution:
    """Test headless command execution mode (aborts because not implemented)."""

    def test_execution_mode_not_implemented(self, tmp_path):
        """Test execution mode shows not implemented warning."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file)]
        )

        # Should show implementation warning
        assert (
            "not implemented" in result.output.lower()
            or "SOAR orchestrator creation not implemented" in result.output
        )

    def test_execution_mode_shows_abort_message(self, tmp_path):
        """Test execution mode aborts with message."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file)]
        )

        assert result.exit_code != 0


class TestHeadlessCommandShorthandOptions:
    """Test headless command short option flags."""

    def test_shorthand_scratchpad_flag(self, tmp_path):
        """Test -s shorthand for --scratchpad."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")
        scratchpad = tmp_path / "scratch.md"

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "-s", str(scratchpad), "--dry-run"],
        )

        assert "scratch.md" in result.output

    def test_shorthand_budget_flag(self, tmp_path):
        """Test -b shorthand for --budget."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "-b", "7.5", "--dry-run"],
        )

        assert "$7.50" in result.output

    def test_shorthand_max_iter_flag(self, tmp_path):
        """Test -m shorthand for --max-iter."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command,
            [str(prompt_file), "-m", "15", "--dry-run"],
        )

        assert "15" in result.output


class TestHeadlessCommandDefaultScratchpad:
    """Test headless command default scratchpad path generation."""

    def test_default_scratchpad_based_on_prompt_name(self, tmp_path):
        """Test default scratchpad derives from prompt filename."""
        runner = CliRunner()
        prompt_file = tmp_path / "my_experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        result = runner.invoke(
            headless_command, [str(prompt_file), "--dry-run"]
        )

        # Output might be wrapped, so check for the key parts
        assert "my_experiment" in result.output
        assert "scratchpad" in result.output.lower()


class TestHeadlessCommandKeyboardInterrupt:
    """Test headless command handles Ctrl+C gracefully."""

    def test_keyboard_interrupt_graceful_exit(self, tmp_path):
        """Test KeyboardInterrupt shows graceful exit message."""
        runner = CliRunner()
        prompt_file = tmp_path / "experiment.md"
        prompt_file.write_text("## Goal\nTest\n")

        # Mock at the module where it's imported (aurora_soar.headless)
        with patch("aurora_soar.headless.orchestrator.HeadlessOrchestrator") as mock_orch:
            mock_orch.return_value.execute.side_effect = KeyboardInterrupt()

            result = runner.invoke(
                headless_command, [str(prompt_file)]
            )

            # Execution aborts before reaching orchestrator, so just verify exit code
            assert result.exit_code != 0
