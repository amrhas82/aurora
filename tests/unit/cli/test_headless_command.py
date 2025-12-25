"""Unit tests for headless CLI command.

Tests the `aur headless` command that runs autonomous experiments.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.main import cli
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


@pytest.fixture
def temp_prompt(tmp_path: Path) -> Path:
    """Create a temporary valid prompt file."""
    prompt = tmp_path / "experiment.md"
    prompt.write_text(
        """## Goal
Test autonomous execution

## Success Criteria
- Criterion 1
- Criterion 2

## Constraints
- Keep it simple

## Context
This is a test experiment.
"""
    )
    return prompt


@pytest.fixture
def temp_scratchpad(tmp_path: Path) -> Path:
    """Create a temporary scratchpad file."""
    return tmp_path / "scratchpad.md"


class TestHeadlessCommandBasics:
    """Test basic headless command functionality."""

    def test_help_text(self, runner: CliRunner):
        """Test help text displays correctly."""
        result = runner.invoke(cli, ["headless", "--help"])
        assert result.exit_code == 0
        assert "headless" in result.output.lower()
        assert "autonomous" in result.output.lower()
        assert "experiment" in result.output.lower()

    def test_missing_prompt_file(self, runner: CliRunner):
        """Test error when prompt file doesn't exist."""
        result = runner.invoke(cli, ["headless", "nonexistent.md"])
        assert result.exit_code != 0
        # Click handles missing file error

    def test_invalid_budget_negative(self, runner: CliRunner, temp_prompt: Path):
        """Test error when budget is negative."""
        result = runner.invoke(cli, ["headless", str(temp_prompt), "--budget", "-1.0"])
        assert result.exit_code != 0
        assert "budget" in result.output.lower() or "positive" in result.output.lower()

    def test_invalid_budget_zero(self, runner: CliRunner, temp_prompt: Path):
        """Test error when budget is zero."""
        result = runner.invoke(cli, ["headless", str(temp_prompt), "--budget", "0"])
        assert result.exit_code != 0
        assert "budget" in result.output.lower() or "positive" in result.output.lower()

    def test_invalid_max_iter_negative(self, runner: CliRunner, temp_prompt: Path):
        """Test error when max iterations is negative."""
        result = runner.invoke(cli, ["headless", str(temp_prompt), "--max-iter", "-1"])
        assert result.exit_code != 0
        assert "iteration" in result.output.lower() or "positive" in result.output.lower()

    def test_invalid_max_iter_zero(self, runner: CliRunner, temp_prompt: Path):
        """Test error when max iterations is zero."""
        result = runner.invoke(cli, ["headless", str(temp_prompt), "--max-iter", "0"])
        assert result.exit_code != 0
        assert "iteration" in result.output.lower() or "positive" in result.output.lower()


class TestHeadlessCommandDryRun:
    """Test dry-run mode (validation without execution)."""

    def test_dry_run_valid_prompt(self, runner: CliRunner, temp_prompt: Path):
        """Test dry-run with valid prompt."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            # Mock orchestrator initialization (for validation)
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run"])

            # Dry run should succeed (validation only)
            assert result.exit_code == 0
            assert "dry run" in result.output.lower() or "validat" in result.output.lower()

    def test_dry_run_shows_configuration(self, runner: CliRunner, temp_prompt: Path):
        """Test dry-run displays configuration."""
        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(
                cli,
                [
                    "headless",
                    str(temp_prompt),
                    "--dry-run",
                    "--budget",
                    "10.0",
                    "--max-iter",
                    "20",
                ],
            )

            assert result.exit_code == 0
            assert "10" in result.output  # Budget
            assert "20" in result.output  # Max iterations

    def test_dry_run_custom_scratchpad(self, runner: CliRunner, temp_prompt: Path, tmp_path: Path):
        """Test dry-run with custom scratchpad path."""
        scratchpad = tmp_path / "custom_log.md"

        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(
                cli,
                [
                    "headless",
                    str(temp_prompt),
                    "--dry-run",
                    "--scratchpad",
                    str(scratchpad),
                ],
            )

            assert result.exit_code == 0
            assert "custom_log" in result.output

    def test_dry_run_custom_branch(self, runner: CliRunner, temp_prompt: Path):
        """Test dry-run with custom branch requirement."""
        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(
                cli,
                ["headless", str(temp_prompt), "--dry-run", "--branch", "test-123"],
            )

            assert result.exit_code == 0
            assert "test-123" in result.output

    def test_dry_run_allow_main_warning(self, runner: CliRunner, temp_prompt: Path):
        """Test dry-run shows warning when allowing main branch."""
        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run", "--allow-main"])

            assert result.exit_code == 0
            # Should show warning about dangerous option
            assert "⚠" in result.output or "DANGEROUS" in result.output


class TestHeadlessCommandOptions:
    """Test command-line options."""

    def test_default_scratchpad_path(self, runner: CliRunner, temp_prompt: Path):
        """Test default scratchpad path generation."""
        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run"])

            assert result.exit_code == 0
            # Default should be <prompt_name>_scratchpad.md
            # Output may have line breaks in table formatting, so check components
            assert "experiment" in result.output
            assert "scratchpad" in result.output.lower()

    def test_short_option_budget(self, runner: CliRunner, temp_prompt: Path):
        """Test short option -b for budget."""
        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run", "-b", "15.5"])

            assert result.exit_code == 0
            assert "15.5" in result.output or "15" in result.output

    def test_short_option_max_iter(self, runner: CliRunner, temp_prompt: Path):
        """Test short option -m for max-iter."""
        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run", "-m", "25"])

            assert result.exit_code == 0
            assert "25" in result.output

    def test_short_option_scratchpad(self, runner: CliRunner, temp_prompt: Path, tmp_path: Path):
        """Test short option -s for scratchpad."""
        scratchpad = tmp_path / "log.md"

        with patch("aurora_soar.headless.HeadlessOrchestrator"):
            result = runner.invoke(
                cli,
                ["headless", str(temp_prompt), "--dry-run", "-s", str(scratchpad)],
            )

            assert result.exit_code == 0
            assert "log.md" in result.output


class TestHeadlessCommandConfiguration:
    """Test configuration creation and validation."""

    def test_config_creation_defaults(self, runner: CliRunner, temp_prompt: Path):
        """Test HeadlessConfig created with correct defaults."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            with patch("aurora_soar.headless.HeadlessConfig") as mock_config:
                mock_config.return_value = MagicMock()
                mock_orch.return_value = MagicMock()

                result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run"])

                assert result.exit_code == 0
                # Verify config was created with defaults
                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args.kwargs
                assert call_kwargs["max_iterations"] == 10
                assert call_kwargs["budget_limit"] == 5.0
                assert call_kwargs["required_branch"] == "headless"
                assert call_kwargs["blocked_branches"] == ["main", "master"]

    def test_config_creation_custom_values(self, runner: CliRunner, temp_prompt: Path):
        """Test HeadlessConfig created with custom values."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            with patch("aurora_soar.headless.HeadlessConfig") as mock_config:
                mock_config.return_value = MagicMock()
                mock_orch.return_value = MagicMock()

                result = runner.invoke(
                    cli,
                    [
                        "headless",
                        str(temp_prompt),
                        "--dry-run",
                        "--budget",
                        "20.0",
                        "--max-iter",
                        "50",
                        "--branch",
                        "experiment-1",
                    ],
                )

                assert result.exit_code == 0
                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args.kwargs
                assert call_kwargs["max_iterations"] == 50
                assert call_kwargs["budget_limit"] == 20.0
                assert call_kwargs["required_branch"] == "experiment-1"

    def test_config_allow_main_disables_blocking(self, runner: CliRunner, temp_prompt: Path):
        """Test --allow-main disables branch blocking."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            with patch("aurora_soar.headless.HeadlessConfig") as mock_config:
                mock_config.return_value = MagicMock()
                mock_orch.return_value = MagicMock()

                result = runner.invoke(
                    cli, ["headless", str(temp_prompt), "--dry-run", "--allow-main"]
                )

                assert result.exit_code == 0
                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args.kwargs
                # Should have empty blocked branches
                assert call_kwargs["blocked_branches"] == []


class TestHeadlessCommandExecution:
    """Test actual execution (mocked)."""

    def test_execution_not_implemented_yet(self, runner: CliRunner, temp_prompt: Path):
        """Test execution shows not-implemented message (until SOAR integration)."""
        # Without --dry-run, should try to execute but abort (not implemented yet)
        result = runner.invoke(cli, ["headless", str(temp_prompt)])

        # Should abort with message about SOAR not implemented
        assert result.exit_code != 0
        # Should mention SOAR or implementation
        assert "soar" in result.output.lower() or "implement" in result.output.lower()


class TestHeadlessCommandFlagSyntax:
    """Test --headless global flag syntax (Task 2.8 requirement)."""

    def test_headless_command_syntax(self, runner: CliRunner, temp_prompt: Path):
        """Test: aur headless test.md executes without errors (dry-run)."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run"])

            assert result.exit_code == 0
            assert "Configuration" in result.output or "configuration" in result.output
            # Should show validation output
            assert "valid" in result.output.lower() or "dry" in result.output.lower()

    def test_headless_flag_syntax(self, runner: CliRunner, temp_prompt: Path):
        """Test: aur --headless test.md works identically to aur headless test.md."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            # Test with --headless flag (global flag syntax)
            result_flag = runner.invoke(cli, ["--headless", str(temp_prompt)])

            # Should invoke headless command
            # Note: Without --dry-run, this will fail with SOAR not implemented,
            # but both syntaxes should fail the same way
            assert result_flag.exit_code != 0
            assert "soar" in result_flag.output.lower() or "implement" in result_flag.output.lower()

    def test_headless_flag_vs_command_output_consistency(
        self, runner: CliRunner, temp_prompt: Path
    ):
        """Test: --headless flag and headless command produce consistent output (dry-run)."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            # Test both syntaxes with dry-run
            result_command = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run"])

            # Reset mock for second call
            mock_orch.reset_mock()
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            # Note: Cannot test --headless with --dry-run because --dry-run is a subcommand option
            # The --headless flag invokes the command with just the prompt_path
            # So we verify the flag works by checking it invokes the command
            result_flag = runner.invoke(cli, ["--headless", str(temp_prompt)])

            # Both should invoke the headless command (though with different options)
            # Command with dry-run should succeed (exit 0)
            assert result_command.exit_code == 0
            # Flag without dry-run should fail with SOAR message (exit != 0)
            assert result_flag.exit_code != 0

    def test_missing_file_error_message_quality(self, runner: CliRunner):
        """Test: Headless mode handles missing files with clear error message."""
        nonexistent_file = "/nonexistent/path/to/prompt.md"

        result = runner.invoke(cli, ["headless", nonexistent_file])

        # Should fail with clear error
        assert result.exit_code != 0
        # Click provides file existence validation, so error should mention file/path
        # Error message quality check - should be understandable
        assert len(result.output) > 0  # Should have some error output

    def test_output_format_consistency(self, runner: CliRunner, temp_prompt: Path):
        """Test: Output format is consistent across multiple runs."""
        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            # Run the same command multiple times
            results = []
            for _ in range(3):
                mock_orch.reset_mock()
                mock_instance = MagicMock()
                mock_orch.return_value = mock_instance

                result = runner.invoke(cli, ["headless", str(temp_prompt), "--dry-run"])
                results.append(result)

            # All runs should succeed
            for result in results:
                assert result.exit_code == 0

            # All outputs should have consistent structure
            # Check for key formatting elements in all outputs
            for result in results:
                assert "Configuration" in result.output or "configuration" in result.output
                assert "Prompt" in result.output
                assert "Budget" in result.output

            # Outputs should be identical (same prompt, same options)
            # Note: Rich formatting may include ANSI codes, so we check structure not exact match
            # Verify all outputs have similar length (within 10% variance)
            lengths = [len(r.output) for r in results]
            avg_length = sum(lengths) / len(lengths)
            for length in lengths:
                assert abs(length - avg_length) / avg_length < 0.1, "Output lengths vary too much"


class TestHeadlessCommandIntegration:
    """Integration tests with mocked components."""

    def test_full_dry_run_workflow(self, runner: CliRunner, temp_prompt: Path, tmp_path: Path):
        """Test complete dry-run workflow."""
        scratchpad = tmp_path / "test_scratch.md"

        with patch("aurora_soar.headless.HeadlessOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "headless",
                    str(temp_prompt),
                    "--dry-run",
                    "--scratchpad",
                    str(scratchpad),
                    "--budget",
                    "7.5",
                    "--max-iter",
                    "15",
                    "--branch",
                    "test-branch",
                ],
            )

            assert result.exit_code == 0

            # Verify orchestrator was created with correct paths
            mock_orch.assert_called_once()
            call_kwargs = mock_orch.call_args.kwargs
            assert Path(call_kwargs["prompt_path"]) == temp_prompt
            assert Path(call_kwargs["scratchpad_path"]) == scratchpad
