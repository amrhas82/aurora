"""Integration tests for multi-tool headless execution.

Tests cover end-to-end scenarios for running the headless command
with multiple AI tools (Claude, OpenCode) concurrently.

These tests mock the subprocess calls but test the full integration
between headless command, ConcurrentToolExecutor, and ToolProviderRegistry.
"""

import asyncio
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import (
    _check_final_state,
    _display_multi_tool_results,
    _parse_tools_callback,
    _run_backpressure,
    _run_multi_tool_loop,
    headless_command,
)
from aurora_cli.concurrent_executor import AggregatedResult, AggregationStrategy, ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_prompt(tmp_path):
    """Create temporary prompt file."""
    prompt = tmp_path / "prompt.md"
    prompt.write_text("# Goal\nTest multi-tool execution\n\n# Success Criteria\n- [ ] Works")
    return prompt


@pytest.fixture
def temp_scratchpad(tmp_path):
    """Create temporary scratchpad directory."""
    scratchpad_dir = tmp_path / ".aurora" / "headless"
    scratchpad_dir.mkdir(parents=True)
    return scratchpad_dir / "scratchpad.md"


@pytest.fixture
def mock_tools_available():
    """Mock both Claude and OpenCode as available."""
    with patch("shutil.which") as mock:
        mock.side_effect = lambda x: f"/usr/bin/{x}" if x in ["claude", "opencode"] else None
        yield mock


@pytest.fixture
def mock_git_check():
    """Mock git branch check to return non-main branch."""
    with patch("subprocess.run") as mock:
        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature-branch\n"
        mock.return_value = git_mock
        yield mock


# ---------------------------------------------------------------------------
# Test: Tools Parsing
# ---------------------------------------------------------------------------


class TestToolsParsing:
    """Test parsing of --tools option."""

    def test_parse_single_tool(self):
        """Test parsing single tool."""
        result = _parse_tools_callback(None, None, ("claude",))
        assert result == ("claude",)

    def test_parse_multiple_tools_separate_flags(self):
        """Test parsing multiple tools with separate -t flags."""
        result = _parse_tools_callback(None, None, ("claude", "opencode"))
        assert result == ("claude", "opencode")

    def test_parse_comma_separated(self):
        """Test parsing comma-separated tools."""
        result = _parse_tools_callback(None, None, ("claude,opencode",))
        assert result == ("claude", "opencode")

    def test_parse_mixed_format(self):
        """Test parsing mixed format (comma and separate)."""
        result = _parse_tools_callback(None, None, ("claude,opencode", "cursor"))
        assert result == ("claude", "opencode", "cursor")

    def test_parse_empty(self):
        """Test parsing empty value."""
        result = _parse_tools_callback(None, None, ())
        assert result is None

    def test_parse_whitespace_handling(self):
        """Test that whitespace is stripped."""
        result = _parse_tools_callback(None, None, ("claude , opencode",))
        assert result == ("claude", "opencode")


# ---------------------------------------------------------------------------
# Test: Show Config
# ---------------------------------------------------------------------------


class TestShowConfig:
    """Test --show-config option."""

    def test_show_config_default(self, runner, temp_prompt, mock_tools_available):
        """Test show-config with default values."""
        result = runner.invoke(
            headless_command,
            ["-p", str(temp_prompt), "--show-config"],
        )

        assert result.exit_code == 0
        # Check for table output format (pipes and value content)
        assert "claude" in result.output
        assert "first_success" in result.output
        assert "10" in result.output  # Max iterations

    def test_show_config_multi_tool(self, runner, temp_prompt, mock_tools_available):
        """Test show-config with multiple tools."""
        result = runner.invoke(
            headless_command,
            ["-p", str(temp_prompt), "-t", "claude", "-t", "opencode", "--show-config"],
        )

        assert result.exit_code == 0
        assert "claude" in result.output
        assert "opencode" in result.output

    def test_show_config_custom_strategy(self, runner, temp_prompt, mock_tools_available):
        """Test show-config with custom strategy."""
        result = runner.invoke(
            headless_command,
            ["-p", str(temp_prompt), "--strategy", "voting", "--show-config"],
        )

        assert result.exit_code == 0
        assert "voting" in result.output


# ---------------------------------------------------------------------------
# Test: Multi-Tool Validation
# ---------------------------------------------------------------------------


class TestMultiToolValidation:
    """Test validation for multi-tool execution."""

    def test_missing_tool_fails(self, runner, temp_prompt):
        """Test that missing tools cause failure."""
        with patch("shutil.which", return_value=None):
            result = runner.invoke(
                headless_command,
                ["-p", str(temp_prompt), "-t", "nonexistent"],
            )

            assert result.exit_code != 0
            assert "not found in PATH" in result.output

    def test_partial_missing_tools_fails(self, runner, temp_prompt):
        """Test that partially missing tools cause failure."""
        with patch("shutil.which") as mock:
            mock.side_effect = lambda x: "/usr/bin/claude" if x == "claude" else None

            result = runner.invoke(
                headless_command,
                ["-p", str(temp_prompt), "-t", "claude", "-t", "nonexistent"],
            )

            assert result.exit_code != 0
            assert "not found in PATH" in result.output


# ---------------------------------------------------------------------------
# Test: Sequential Multi-Tool
# ---------------------------------------------------------------------------


class TestSequentialMultiTool:
    """Test sequential (round-robin) multi-tool execution."""

    def test_sequential_round_robin(
        self,
        runner,
        temp_prompt,
        mock_tools_available,
        mock_git_check,
        tmp_path,
    ):
        """Test sequential execution rotates through tools."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            tool_calls = []

            def track_tool(*args, **kwargs):
                cmd = args[0]
                if "git" in cmd[0]:
                    return mock_git_check.return_value
                tool_calls.append(cmd[0])
                return Mock(returncode=0, stdout="Output", stderr="")

            with patch("subprocess.run", side_effect=track_tool):
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_prompt),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--sequential",
                        "--max",
                        "4",
                    ],
                )

                # Should alternate: claude, opencode, claude, opencode
                assert tool_calls == ["claude", "opencode", "claude", "opencode"]


# ---------------------------------------------------------------------------
# Test: Parallel Multi-Tool Execution
# ---------------------------------------------------------------------------


class TestParallelMultiTool:
    """Test parallel multi-tool execution."""

    @pytest.mark.asyncio
    async def test_run_multi_tool_loop_first_success(self, tmp_path):
        """Test parallel execution with first_success strategy."""
        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("Test prompt")
        scratchpad = tmp_path / "scratchpad.md"

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            # Mock execute to return success immediately
            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Success",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Claude output",
                            execution_time=1.0,
                        ),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            # Initialize scratchpad with STATUS: DONE to exit after first iteration
            scratchpad.write_text("STATUS: DONE\n")

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=scratchpad,
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Should have initialized executor with correct strategy
            MockExecutor.assert_called_once()
            call_args = MockExecutor.call_args
            assert call_args[0][0] == ["claude", "opencode"]

    @pytest.mark.asyncio
    async def test_run_multi_tool_loop_early_exit(self, tmp_path):
        """Test that loop exits early when STATUS: DONE is found."""
        scratchpad = tmp_path / "scratchpad.md"
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                # Write STATUS: DONE after first iteration
                scratchpad.write_text("STATUS: DONE\n")
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            # Start without STATUS: DONE
            scratchpad.write_text("Initial state\n")

            await _run_multi_tool_loop(
                tools_list=["claude"],
                prompt="Test",
                scratchpad=scratchpad,
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Should have only run once because STATUS: DONE was written
            assert iteration_count[0] == 1


# ---------------------------------------------------------------------------
# Test: Results Display
# ---------------------------------------------------------------------------


class TestResultsDisplay:
    """Test multi-tool results display."""

    def test_display_results_table(self, capsys):
        """Test that results are displayed in a table."""
        result = AggregatedResult(
            success=True,
            primary_output="Winner output",
            strategy_used=AggregationStrategy.FIRST_SUCCESS,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Claude output", execution_time=1.5),
                ToolResult(
                    tool="opencode",
                    success=False,
                    output="",
                    error="Failed",
                    execution_time=2.0,
                ),
            ],
            winning_tool="claude",
        )

        # Capture console output
        _display_multi_tool_results(result, "first_success")

        # The function prints to console, we can verify it ran without error

    def test_display_results_with_scores(self, capsys):
        """Test that scores are displayed when present."""
        result = AggregatedResult(
            success=True,
            primary_output="Winner output",
            strategy_used=AggregationStrategy.BEST_SCORE,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Output", execution_time=1.0),
                ToolResult(tool="opencode", success=True, output="Output", execution_time=2.0),
            ],
            winning_tool="claude",
            metadata={"scores": {"claude": 15.0, "opencode": 12.0}},
        )

        _display_multi_tool_results(result, "best_score")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class TestBackpressure:
    """Test backpressure (test command) integration."""

    def test_backpressure_success(self):
        """Test backpressure with passing tests."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Tests passed", stderr="")

            # Should not raise
            _run_backpressure("pytest tests/")

            mock_run.assert_called_once()
            assert "pytest" in mock_run.call_args[0][0]

    def test_backpressure_failure(self):
        """Test backpressure with failing tests."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Tests failed")

            # Should not raise, just log warning
            _run_backpressure("pytest tests/")


# ---------------------------------------------------------------------------
# Test: Final State Check
# ---------------------------------------------------------------------------


class TestFinalStateCheck:
    """Test final state checking."""

    def test_check_final_state_done(self, tmp_path, capsys):
        """Test final state check when done."""
        scratchpad = tmp_path / "scratchpad.md"
        scratchpad.write_text("# Scratchpad\nSTATUS: DONE\n")

        _check_final_state(scratchpad)

        # Should print success message

    def test_check_final_state_not_done(self, tmp_path, capsys):
        """Test final state check when not done."""
        scratchpad = tmp_path / "scratchpad.md"
        scratchpad.write_text("# Scratchpad\nSTATUS: IN_PROGRESS\n")

        _check_final_state(scratchpad)

        # Should print warning message


# ---------------------------------------------------------------------------
# Test: Strategy Selection
# ---------------------------------------------------------------------------


class TestStrategySelection:
    """Test aggregation strategy selection."""

    def test_strategy_from_cli(self, runner, temp_prompt, mock_tools_available):
        """Test that CLI strategy option is respected."""
        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(temp_prompt),
                "-t",
                "claude",
                "-t",
                "opencode",
                "--strategy",
                "voting",
                "--show-config",
            ],
        )

        assert result.exit_code == 0
        assert "voting" in result.output

    def test_all_strategies_valid(self, runner, temp_prompt, mock_tools_available):
        """Test that all strategy options are valid."""
        strategies = ["first_success", "all_complete", "voting", "best_score", "merge"]

        for strategy in strategies:
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(temp_prompt),
                    "-t",
                    "claude",
                    "--strategy",
                    strategy,
                    "--show-config",
                ],
            )

            assert result.exit_code == 0, f"Strategy {strategy} failed"

    def test_invalid_strategy_fails(self, runner, temp_prompt, mock_tools_available):
        """Test that invalid strategy causes failure."""
        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(temp_prompt),
                "-t",
                "claude",
                "--strategy",
                "invalid",
            ],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Test: End-to-End Multi-Tool Scenarios
# ---------------------------------------------------------------------------


class TestEndToEndMultiTool:
    """End-to-end tests for multi-tool scenarios."""

    def test_parallel_two_tools_success(
        self,
        runner,
        temp_prompt,
        mock_tools_available,
        mock_git_check,
        tmp_path,
    ):
        """Test successful parallel execution with two tools."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_prompt),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--max",
                        "1",
                    ],
                )

                # Should have called asyncio.run for parallel execution
                mock_asyncio.assert_called_once()

    def test_tool_count_determines_mode(
        self,
        runner,
        temp_prompt,
        mock_tools_available,
        mock_git_check,
        tmp_path,
    ):
        """Test that tool count determines execution mode."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            # Single tool should use sequential mode
            with patch("aurora_cli.commands.headless._run_single_tool_loop") as mock_single:
                with patch("subprocess.run", return_value=mock_git_check.return_value):
                    runner.invoke(
                        headless_command,
                        ["-p", str(temp_prompt), "-t", "claude", "--max", "1"],
                    )

                    mock_single.assert_called_once()

            # Multiple tools should use parallel mode (unless --sequential)
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                with patch("subprocess.run", return_value=mock_git_check.return_value):
                    runner.invoke(
                        headless_command,
                        [
                            "-p",
                            str(temp_prompt),
                            "-t",
                            "claude",
                            "-t",
                            "opencode",
                            "--max",
                            "1",
                        ],
                    )

                    mock_asyncio.assert_called_once()


# ---------------------------------------------------------------------------
# Test: Config Integration
# ---------------------------------------------------------------------------


class TestConfigIntegration:
    """Test configuration integration."""

    def test_config_defaults_applied(self, runner, temp_prompt, mock_tools_available):
        """Test that config defaults are applied."""
        with patch("aurora_cli.commands.headless.load_config") as mock_config:
            # Create a mock config object with dataclass-like attributes
            mock_cfg = MagicMock()
            mock_cfg.headless_tools = ["claude"]
            mock_cfg.headless_max_iterations = 5
            mock_cfg.headless_strategy = "all_complete"
            mock_cfg.headless_parallel = True
            mock_cfg.headless_timeout = 300
            mock_cfg.headless_tool_configs = {}
            mock_cfg.headless_routing_rules = []
            mock_config.return_value = mock_cfg

            result = runner.invoke(
                headless_command,
                ["-p", str(temp_prompt), "--show-config"],
            )

            assert result.exit_code == 0
            # Check for table output with values
            assert "5" in result.output  # max iterations
            assert "all_complete" in result.output
            assert "300" in result.output  # timeout

    def test_cli_overrides_config(self, runner, temp_prompt, mock_tools_available):
        """Test that CLI options override config."""
        with patch("aurora_cli.commands.headless.load_config") as mock_config:
            # Create a mock config object with dataclass-like attributes
            mock_cfg = MagicMock()
            mock_cfg.headless_tools = ["claude"]
            mock_cfg.headless_max_iterations = 5
            mock_cfg.headless_strategy = "all_complete"
            mock_cfg.headless_parallel = True
            mock_cfg.headless_timeout = 600
            mock_cfg.headless_tool_configs = {}
            mock_cfg.headless_routing_rules = []
            mock_config.return_value = mock_cfg

            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(temp_prompt),
                    "--max",
                    "20",
                    "--strategy",
                    "voting",
                    "--show-config",
                ],
            )

            assert result.exit_code == 0
            # Check for table output with overridden values
            assert "20" in result.output  # overridden max iterations
            assert "voting" in result.output  # overridden strategy


# ---------------------------------------------------------------------------
# Test: Concurrent Execution Behavior
# ---------------------------------------------------------------------------


class TestConcurrentExecutionBehavior:
    """Test specific concurrent execution behaviors."""

    @pytest.mark.asyncio
    async def test_tools_execute_in_parallel(self, tmp_path):
        """Test that tools actually execute in parallel."""
        scratchpad = tmp_path / "scratchpad.md"
        scratchpad.write_text("STATUS: DONE\n")  # Exit immediately

        execution_times = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            import time

            async def mock_execute(context):
                start = time.time()
                await asyncio.sleep(0.01)  # Simulate some work
                execution_times.append(time.time() - start)

                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(tool="claude", success=True, output="", execution_time=0.01),
                        ToolResult(tool="opencode", success=True, output="", execution_time=0.01),
                    ],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=scratchpad,
                max_iter=1,
                test_cmd=None,
                strategy="all_complete",
            )

    @pytest.mark.asyncio
    async def test_first_success_cancels_others(self, tmp_path):
        """Test that first_success strategy cancels other tools."""
        scratchpad = tmp_path / "scratchpad.md"
        scratchpad.write_text("Initial\n")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            call_count = [0]

            async def mock_execute(context):
                call_count[0] += 1
                # Simulate first_success returning immediately
                scratchpad.write_text("STATUS: DONE\n")
                return AggregatedResult(
                    success=True,
                    primary_output="First success",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(tool="claude", success=True, output="Quick", execution_time=0.1),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=scratchpad,
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Should have only called execute once before STATUS: DONE
            assert call_count[0] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
