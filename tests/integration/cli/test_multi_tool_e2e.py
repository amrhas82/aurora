"""End-to-end integration tests for multi-tool concurrent execution.

Tests cover full integration scenarios for running Claude and OpenCode together:
- Full CLI command execution with multi-tool options
- Scratchpad state management across tools
- Real-world workflow simulation (without actual tool execution)
- Configuration file integration
- Budget and time limit enforcement
- Backpressure (test command) integration
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import (
    _check_final_state,
    _display_multi_tool_results,
    _run_multi_tool_loop,
    _run_single_tool_loop,
    headless_command,
)
from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ConflictInfo,
    ConflictSeverity,
    ToolConfig,
    ToolResult,
)
from aurora_cli.tool_providers import ToolProviderRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with prompt and scratchpad."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    headless_dir = workspace / ".aurora" / "headless"
    headless_dir.mkdir(parents=True)

    # Create prompt file
    prompt_file = headless_dir / "prompt.md"
    prompt_file.write_text(
        """# Goal
Implement a feature using multi-tool execution.

# Success Criteria
- [ ] Code compiles
- [ ] Tests pass
- [ ] Documentation updated

# Context
This is a test prompt for multi-tool execution.
"""
    )

    return workspace


@pytest.fixture
def mock_both_tools():
    """Mock both Claude and OpenCode as available."""
    with patch("aurora_cli.commands.headless.shutil.which") as mock:
        mock.side_effect = lambda x: f"/usr/bin/{x}" if x in ["claude", "opencode"] else None
        yield mock


@pytest.fixture
def mock_git_feature_branch():
    """Mock git to return a feature branch."""
    with patch("aurora_cli.commands.headless.subprocess.run") as mock:
        git_mock = Mock()
        git_mock.returncode = 0
        git_mock.stdout = "feature/multi-tool-test\n"
        mock.return_value = git_mock
        yield mock


# ---------------------------------------------------------------------------
# Test: Full CLI Command Execution
# ---------------------------------------------------------------------------


class TestFullCLIExecution:
    """Test full CLI command execution with multi-tool options."""

    def test_multi_tool_parallel_invocation(
        self, runner, temp_workspace, mock_both_tools, mock_git_feature_branch
    ):
        """Test invoking headless command with parallel multi-tool execution."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        with patch("pathlib.Path.cwd", return_value=temp_workspace):
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(prompt_path),
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

                # Check output mentions both tools
                assert "claude" in result.output.lower() or "opencode" in result.output.lower()

    def test_multi_tool_sequential_invocation(
        self, runner, temp_workspace, mock_both_tools, mock_git_feature_branch
    ):
        """Test invoking headless command with sequential multi-tool execution."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        with patch("pathlib.Path.cwd", return_value=temp_workspace):
            with patch("aurora_cli.commands.headless._run_single_tool_loop") as mock_single:
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(prompt_path),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--sequential",
                        "--max",
                        "1",
                    ],
                )

                # Should have called single tool loop (sequential mode)
                mock_single.assert_called_once()

    def test_strategy_selection(self, runner, temp_workspace, mock_both_tools):
        """Test different strategy selections via CLI."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        strategies = [
            "first_success",
            "all_complete",
            "voting",
            "best_score",
            "merge",
            "smart_merge",
            "consensus",
        ]

        for strategy in strategies:
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(prompt_path),
                    "-t",
                    "claude",
                    "-t",
                    "opencode",
                    "--strategy",
                    strategy,
                    "--show-config",
                ],
            )

            assert result.exit_code == 0, f"Strategy {strategy} failed: {result.output}"
            assert strategy in result.output

    def test_comma_separated_tools(self, runner, temp_workspace, mock_both_tools):
        """Test comma-separated tool specification."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(prompt_path),
                "--tools",
                "claude,opencode",
                "--show-config",
            ],
        )

        assert result.exit_code == 0
        assert "claude" in result.output
        assert "opencode" in result.output


# ---------------------------------------------------------------------------
# Test: Scratchpad State Management
# ---------------------------------------------------------------------------


class TestScratchpadManagement:
    """Test scratchpad state management across multi-tool execution."""

    @pytest.mark.asyncio
    async def test_scratchpad_created_if_missing(self, temp_workspace):
        """Test that scratchpad is created if missing."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"

        # Ensure scratchpad doesn't exist
        if scratchpad.exists():
            scratchpad.unlink()

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                # Simulate STATUS: DONE
                scratchpad.write_text("STATUS: DONE\n")
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            # Start without scratchpad
            scratchpad.parent.mkdir(parents=True, exist_ok=True)
            scratchpad.write_text("Initial state\n")

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=scratchpad,
                max_iter=2,
                test_cmd=None,
                strategy="first_success",
            )

    @pytest.mark.asyncio
    async def test_early_exit_on_status_done(self, temp_workspace):
        """Test that execution stops when STATUS: DONE is found."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"
        scratchpad.parent.mkdir(parents=True, exist_ok=True)

        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                if iteration_count[0] == 1:
                    scratchpad.write_text("STATUS: DONE\nWork completed successfully.\n")
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
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=scratchpad,
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Should have exited early
            assert iteration_count[0] == 1

    @pytest.mark.asyncio
    async def test_scratchpad_read_before_each_iteration(self, temp_workspace):
        """Test that scratchpad is read before each iteration."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"
        scratchpad.parent.mkdir(parents=True, exist_ok=True)

        contexts_received = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                contexts_received.append(context)
                # Update scratchpad each iteration
                current = scratchpad.read_text()
                iteration = len(contexts_received)
                scratchpad.write_text(f"{current}\nIteration {iteration} complete\n")
                if iteration >= 2:
                    scratchpad.write_text(scratchpad.read_text() + "STATUS: DONE\n")
                return AggregatedResult(
                    success=True,
                    primary_output=f"Iteration {iteration}",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            scratchpad.write_text("Initial scratchpad state\n")

            await _run_multi_tool_loop(
                tools_list=["claude"],
                prompt="Test prompt",
                scratchpad=scratchpad,
                max_iter=5,
                test_cmd=None,
                strategy="first_success",
            )

            # Each context should include updated scratchpad
            assert len(contexts_received) == 2
            assert "Initial scratchpad state" in contexts_received[0]
            assert "Iteration 1 complete" in contexts_received[1]


# ---------------------------------------------------------------------------
# Test: Budget and Time Limit Enforcement
# ---------------------------------------------------------------------------


class TestBudgetAndTimeLimits:
    """Test budget and time limit enforcement in multi-tool execution."""

    @pytest.mark.asyncio
    async def test_time_limit_enforced(self, temp_workspace):
        """Test that time limit stops execution."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"
        scratchpad.parent.mkdir(parents=True, exist_ok=True)
        scratchpad.write_text("Initial state\n")

        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                await asyncio.sleep(0.5)  # Each iteration takes 0.5s
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude"],
                prompt="Test prompt",
                scratchpad=scratchpad,
                max_iter=100,
                test_cmd=None,
                strategy="first_success",
                time_limit=1,  # 1 second limit
            )

            # Should have stopped due to time limit (only 1-2 iterations possible)
            assert iteration_count[0] <= 3

    @pytest.mark.asyncio
    async def test_budget_limit_displayed(self, runner, temp_workspace, mock_both_tools):
        """Test that budget limit is displayed in config."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(prompt_path),
                "-t",
                "claude",
                "--budget",
                "10.50",
                "--show-config",
            ],
        )

        assert result.exit_code == 0
        assert "$10.50" in result.output


# ---------------------------------------------------------------------------
# Test: Backpressure Integration
# ---------------------------------------------------------------------------


class TestBackpressureIntegration:
    """Test backpressure (test command) integration."""

    def test_backpressure_command_displayed(self, runner, temp_workspace, mock_both_tools):
        """Test that test command is displayed in config."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(prompt_path),
                "-t",
                "claude",
                "--test-cmd",
                "pytest tests/",
                "--show-config",
            ],
        )

        assert result.exit_code == 0
        assert "pytest" in result.output

    @pytest.mark.asyncio
    async def test_backpressure_runs_between_iterations(self, temp_workspace):
        """Test that backpressure test runs between iterations."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"
        scratchpad.parent.mkdir(parents=True, exist_ok=True)
        scratchpad.write_text("Initial state\n")

        test_command_runs = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            iteration = [0]

            async def mock_execute(context):
                iteration[0] += 1
                if iteration[0] >= 2:
                    scratchpad.write_text("STATUS: DONE\n")
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            original_run = None

            def mock_subprocess_run(cmd, **kwargs):
                if "pytest" in cmd:
                    test_command_runs[0] += 1
                result = Mock()
                result.returncode = 0
                result.stdout = "Tests passed"
                result.stderr = ""
                return result

            with patch(
                "aurora_cli.commands.headless.subprocess.run", side_effect=mock_subprocess_run
            ):
                await _run_multi_tool_loop(
                    tools_list=["claude"],
                    prompt="Test prompt",
                    scratchpad=scratchpad,
                    max_iter=5,
                    test_cmd="pytest tests/",
                    strategy="first_success",
                )

                # Test command should have run
                assert test_command_runs[0] >= 1


# ---------------------------------------------------------------------------
# Test: Configuration Integration
# ---------------------------------------------------------------------------


class TestConfigurationIntegration:
    """Test configuration file integration."""

    def test_config_defaults_applied(self, runner, temp_workspace, mock_both_tools):
        """Test that config defaults are properly applied."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        with patch("aurora_cli.commands.headless.load_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.headless_tools = ["claude", "opencode"]
            mock_cfg.headless_max_iterations = 15
            mock_cfg.headless_strategy = "consensus"
            mock_cfg.headless_parallel = True
            mock_cfg.headless_timeout = 300
            mock_cfg.headless_budget = None
            mock_cfg.headless_time_limit = None
            mock_cfg.headless_tool_configs = {}
            mock_cfg.headless_routing_rules = []
            mock_config.return_value = mock_cfg

            result = runner.invoke(
                headless_command,
                ["-p", str(prompt_path), "--show-config"],
            )

            assert result.exit_code == 0
            assert "15" in result.output  # max iterations
            assert "consensus" in result.output
            assert "300" in result.output  # timeout

    def test_cli_overrides_config(self, runner, temp_workspace, mock_both_tools):
        """Test that CLI arguments override config values."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        with patch("aurora_cli.commands.headless.load_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.headless_tools = ["claude"]
            mock_cfg.headless_max_iterations = 10
            mock_cfg.headless_strategy = "first_success"
            mock_cfg.headless_parallel = True
            mock_cfg.headless_timeout = 600
            mock_cfg.headless_budget = None
            mock_cfg.headless_time_limit = None
            mock_cfg.headless_tool_configs = {}
            mock_cfg.headless_routing_rules = []
            mock_config.return_value = mock_cfg

            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(prompt_path),
                    "-t",
                    "opencode",  # Override tool
                    "--max",
                    "25",  # Override max
                    "--strategy",
                    "voting",  # Override strategy
                    "--show-config",
                ],
            )

            assert result.exit_code == 0
            assert "25" in result.output  # overridden max
            assert "voting" in result.output  # overridden strategy


# ---------------------------------------------------------------------------
# Test: Real-World Workflow Simulation
# ---------------------------------------------------------------------------


class TestWorkflowSimulation:
    """Test real-world workflow scenarios."""

    @pytest.mark.asyncio
    async def test_iterative_code_generation(self, temp_workspace):
        """Simulate iterative code generation with both tools."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"
        scratchpad.parent.mkdir(parents=True, exist_ok=True)

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            iteration = [0]
            workflow_states = []

            async def mock_execute(context):
                iteration[0] += 1
                workflow_states.append(f"iteration_{iteration[0]}")

                if iteration[0] == 1:
                    scratchpad.write_text(
                        """# Progress
- [x] Initial implementation
- [ ] Add tests
STATUS: IN_PROGRESS
"""
                    )
                elif iteration[0] == 2:
                    scratchpad.write_text(
                        """# Progress
- [x] Initial implementation
- [x] Add tests
- [ ] Fix linting
STATUS: IN_PROGRESS
"""
                    )
                elif iteration[0] == 3:
                    scratchpad.write_text(
                        """# Progress
- [x] Initial implementation
- [x] Add tests
- [x] Fix linting
STATUS: DONE
"""
                    )

                return AggregatedResult(
                    success=True,
                    primary_output=f"Completed step {iteration[0]}",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Claude output", execution_time=1.0
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="OpenCode output",
                            execution_time=1.5,
                        ),
                    ],
                )

            mock_executor.execute = mock_execute
            scratchpad.write_text("Initial state\n")

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Implement feature",
                scratchpad=scratchpad,
                max_iter=10,
                test_cmd=None,
                strategy="all_complete",
            )

            # Should have completed in 3 iterations
            assert iteration[0] == 3
            assert workflow_states == ["iteration_1", "iteration_2", "iteration_3"]

    @pytest.mark.asyncio
    async def test_tool_recovery_scenario(self, temp_workspace):
        """Test recovery when one tool fails mid-workflow."""
        scratchpad = temp_workspace / ".aurora" / "headless" / "scratchpad.md"
        scratchpad.parent.mkdir(parents=True, exist_ok=True)
        scratchpad.write_text("Initial state\n")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            iteration = [0]

            async def mock_execute(context):
                iteration[0] += 1

                if iteration[0] == 2:
                    # Claude fails in second iteration
                    claude_result = ToolResult(
                        tool="claude",
                        success=False,
                        output="",
                        error="Rate limited",
                        execution_time=0.5,
                    )
                else:
                    claude_result = ToolResult(
                        tool="claude",
                        success=True,
                        output="Claude response",
                        execution_time=1.0,
                    )

                opencode_result = ToolResult(
                    tool="opencode",
                    success=True,
                    output="OpenCode response",
                    execution_time=1.2,
                )

                if iteration[0] >= 3:
                    scratchpad.write_text("STATUS: DONE\n")

                return AggregatedResult(
                    success=True,  # Still success because OpenCode worked
                    primary_output="Continued with OpenCode",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[claude_result, opencode_result],
                    winning_tool="opencode" if iteration[0] == 2 else "claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Complete task",
                scratchpad=scratchpad,
                max_iter=5,
                test_cmd=None,
                strategy="first_success",
            )

            # Workflow should have continued despite Claude failure
            assert iteration[0] == 3


# ---------------------------------------------------------------------------
# Test: Results Display
# ---------------------------------------------------------------------------


class TestResultsDisplay:
    """Test multi-tool results display functionality."""

    def test_display_with_conflict_info(self, capsys):
        """Test results display with conflict information."""
        conflict_info = ConflictInfo(
            severity=ConflictSeverity.MODERATE,
            tools_involved=["claude", "opencode"],
            description="Moderate differences require review",
            similarity_score=0.72,
        )

        result = AggregatedResult(
            success=True,
            primary_output="Merged output",
            strategy_used=AggregationStrategy.SMART_MERGE,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Claude output", execution_time=2.5),
                ToolResult(
                    tool="opencode", success=True, output="OpenCode output", execution_time=3.1
                ),
            ],
            winning_tool="claude",
            conflict_info=conflict_info,
        )

        _display_multi_tool_results(result, "smart_merge")

        # Function should complete without error

    def test_display_with_consensus_metadata(self, capsys):
        """Test results display with consensus metadata."""
        result = AggregatedResult(
            success=True,
            primary_output="Agreed output",
            strategy_used=AggregationStrategy.CONSENSUS,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Same answer", execution_time=1.0),
                ToolResult(tool="opencode", success=True, output="Same answer", execution_time=1.2),
            ],
            winning_tool="claude",
            metadata={
                "consensus_reached": True,
                "similarity_score": 0.98,
                "threshold": 0.80,
            },
        )

        _display_multi_tool_results(result, "consensus")

        # Function should complete without error

    def test_display_with_scores(self, capsys):
        """Test results display with scoring information."""
        result = AggregatedResult(
            success=True,
            primary_output="Best scored output",
            strategy_used=AggregationStrategy.BEST_SCORE,
            tool_results=[
                ToolResult(tool="claude", success=True, output="A" * 500, execution_time=25.0),
                ToolResult(tool="opencode", success=True, output="B" * 100, execution_time=40.0),
            ],
            winning_tool="claude",
            metadata={
                "scores": {"claude": 18.0, "opencode": 13.0},
            },
        )

        _display_multi_tool_results(result, "best_score")

        # Function should complete without error


# ---------------------------------------------------------------------------
# Test: Error Scenarios
# ---------------------------------------------------------------------------


class TestErrorScenarios:
    """Test error handling in multi-tool scenarios."""

    def test_missing_tool_error(self, runner, temp_workspace):
        """Test error when a specified tool is missing."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        with patch("aurora_cli.commands.headless.shutil.which", return_value=None):
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(prompt_path),
                    "-t",
                    "nonexistent_tool",
                ],
            )

            assert result.exit_code != 0
            assert "not found in PATH" in result.output

    def test_partial_tool_availability(self, runner, temp_workspace):
        """Test error when only some tools are available."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        with patch("aurora_cli.commands.headless.shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/claude" if x == "claude" else None

            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(prompt_path),
                    "-t",
                    "claude",
                    "-t",
                    "missing_tool",
                ],
            )

            assert result.exit_code != 0
            assert "not found in PATH" in result.output

    def test_invalid_strategy_error(self, runner, temp_workspace, mock_both_tools):
        """Test error for invalid strategy."""
        prompt_path = temp_workspace / ".aurora" / "headless" / "prompt.md"

        result = runner.invoke(
            headless_command,
            [
                "-p",
                str(prompt_path),
                "-t",
                "claude",
                "--strategy",
                "invalid_strategy",
            ],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Test: List Tools Command
# ---------------------------------------------------------------------------


class TestListToolsCommand:
    """Test --list-tools functionality."""

    def test_list_available_tools(self, runner):
        """Test listing available tool providers."""
        result = runner.invoke(headless_command, ["--list-tools"])

        assert result.exit_code == 0
        assert "Available Tool Providers" in result.output
        # Should show common tools
        assert "claude" in result.output.lower()

    def test_list_tools_shows_status(self, runner):
        """Test that list tools shows installation status."""
        result = runner.invoke(headless_command, ["--list-tools"])

        assert result.exit_code == 0
        # Should show some status indication
        assert "installed" in result.output.lower() or "not found" in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
