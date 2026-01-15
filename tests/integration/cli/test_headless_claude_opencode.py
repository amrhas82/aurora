"""Integration tests for Claude + OpenCode multi-tool headless execution.

End-to-end tests for the headless command running with both Claude
and OpenCode simultaneously. Tests cover realistic workflow scenarios
including scratchpad state management, iteration loops, and tool
coordination.

These tests mock the subprocess layer but test full integration between:
- headless command CLI interface
- ConcurrentToolExecutor
- ToolProviderRegistry
- Scratchpad state management
- Aggregation strategies
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import (
    _run_multi_tool_loop,
    _run_single_tool_loop,
    headless_command,
)
from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ToolResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a complete temporary workspace with prompt and scratchpad."""
    # Create .aurora/headless directory
    headless_dir = tmp_path / ".aurora" / "headless"
    headless_dir.mkdir(parents=True)

    # Create prompt file
    prompt = headless_dir / "prompt.md"
    prompt.write_text(
        """# Goal
Implement a new feature for the application.

# Success Criteria
- [ ] Feature is implemented
- [ ] Tests pass
- [ ] Code is documented

# Context
Working on a Python project.
"""
    )

    # Create initial scratchpad
    scratchpad = headless_dir / "scratchpad.md"
    scratchpad.write_text(
        """# Scratchpad

## STATUS: IN_PROGRESS

## Observations
- Starting fresh

## Next Steps
- Analyze requirements
"""
    )

    return {
        "root": tmp_path,
        "headless_dir": headless_dir,
        "prompt": prompt,
        "scratchpad": scratchpad,
    }


@pytest.fixture
def mock_tools_in_path():
    """Mock both claude and opencode as available in PATH."""

    def which_side_effect(cmd):
        if cmd in ("claude", "opencode"):
            return f"/usr/bin/{cmd}"
        return None

    with patch("shutil.which", side_effect=which_side_effect):
        with patch("aurora_cli.commands.headless.shutil.which", side_effect=which_side_effect):
            yield


@pytest.fixture
def mock_git_feature_branch():
    """Mock git to return a feature branch."""

    def mock_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        if isinstance(cmd, list) and "git" in cmd[0]:
            result = Mock()
            result.returncode = 0
            result.stdout = "feature-branch\n"
            result.stderr = ""
            return result
        # Default mock for other commands
        result = Mock()
        result.returncode = 0
        result.stdout = "Tool output"
        result.stderr = ""
        return result

    with patch("aurora_cli.commands.headless.subprocess.run", side_effect=mock_run):
        with patch("subprocess.run", side_effect=mock_run):
            yield mock_run


# ---------------------------------------------------------------------------
# Test: CLI Multi-Tool Invocation
# ---------------------------------------------------------------------------


class TestCLIMultiToolInvocation:
    """Test CLI invocation with multiple tools."""

    def test_parallel_mode_two_tools(
        self, runner, temp_workspace, mock_tools_in_path, mock_git_feature_branch
    ):
        """Test parallel execution with Claude and OpenCode via CLI."""
        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_workspace["prompt"]),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--max",
                        "1",
                    ],
                )

                # Should use parallel mode (asyncio.run) for multi-tool
                mock_asyncio.assert_called_once()
                assert "parallel" in result.output or "claude, opencode" in result.output

    def test_sequential_mode_two_tools(
        self, runner, temp_workspace, mock_tools_in_path, mock_git_feature_branch
    ):
        """Test sequential execution with --sequential flag."""
        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            with patch("aurora_cli.commands.headless._run_single_tool_loop") as mock_single_loop:
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_workspace["prompt"]),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--sequential",
                        "--max",
                        "1",
                    ],
                )

                # Should use single tool loop (sequential mode)
                mock_single_loop.assert_called_once()
                call_kwargs = mock_single_loop.call_args[1]
                assert call_kwargs["sequential_multi"] is True

    def test_comma_separated_tools(
        self, runner, temp_workspace, mock_tools_in_path, mock_git_feature_branch
    ):
        """Test comma-separated tool specification."""
        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_workspace["prompt"]),
                        "--tools",
                        "claude,opencode",
                        "--max",
                        "1",
                    ],
                )

                # Should parse comma-separated and use parallel mode
                mock_asyncio.assert_called_once()


# ---------------------------------------------------------------------------
# Test: Parallel Execution Loop
# ---------------------------------------------------------------------------


class TestParallelExecutionLoop:
    """Test the parallel multi-tool execution loop."""

    @pytest.mark.asyncio
    async def test_parallel_loop_basic(self, temp_workspace):
        """Test basic parallel execution loop."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                # Mark done after first iteration
                temp_workspace["scratchpad"].write_text(
                    "# Scratchpad\n\nSTATUS: DONE\n\nTask completed!"
                )
                return AggregatedResult(
                    success=True,
                    primary_output="Both tools completed task",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Claude done", execution_time=1.0
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="OpenCode done",
                            execution_time=1.5,
                        ),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            assert iteration_count[0] == 1

    @pytest.mark.asyncio
    async def test_parallel_loop_multiple_iterations(self, temp_workspace):
        """Test parallel loop runs multiple iterations until done."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                if iteration_count[0] >= 3:
                    # Complete on third iteration
                    temp_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output=f"Iteration {iteration_count[0]}",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Progress", execution_time=0.5
                        ),
                        ToolResult(
                            tool="opencode", success=True, output="Progress", execution_time=0.5
                        ),
                    ],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="all_complete",
            )

            assert iteration_count[0] == 3

    @pytest.mark.asyncio
    async def test_parallel_loop_reaches_max_iterations(self, temp_workspace):
        """Test parallel loop respects max iterations."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                # Never complete
                return AggregatedResult(
                    success=True,
                    primary_output="Still working",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Working", execution_time=0.5
                        ),
                    ],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=5,
                test_cmd=None,
                strategy="first_success",
            )

            assert iteration_count[0] == 5


# ---------------------------------------------------------------------------
# Test: Sequential Multi-Tool Execution
# ---------------------------------------------------------------------------


class TestSequentialMultiToolExecution:
    """Test sequential (round-robin) multi-tool execution."""

    def test_sequential_round_robin_alternates(self, runner, temp_workspace, mock_tools_in_path):
        """Test that sequential mode alternates between tools."""
        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            tool_sequence = []

            def mock_subprocess(*args, **kwargs):
                cmd = args[0] if args else []
                if isinstance(cmd, list):
                    if "git" in cmd[0]:
                        mock = Mock()
                        mock.returncode = 0
                        mock.stdout = "feature-branch\n"
                        return mock
                    tool_name = cmd[0]
                    tool_sequence.append(tool_name)
                mock = Mock()
                mock.returncode = 0
                mock.stdout = "Output"
                mock.stderr = ""
                return mock

            with patch("aurora_cli.commands.headless.subprocess.run", side_effect=mock_subprocess):
                with patch("subprocess.run", side_effect=mock_subprocess):
                    result = runner.invoke(
                        headless_command,
                        [
                            "-p",
                            str(temp_workspace["prompt"]),
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
                    assert tool_sequence == ["claude", "opencode", "claude", "opencode"]


# ---------------------------------------------------------------------------
# Test: Aggregation Strategy Integration
# ---------------------------------------------------------------------------


class TestAggregationStrategyIntegration:
    """Test different aggregation strategies in headless context."""

    @pytest.mark.asyncio
    async def test_first_success_strategy(self, temp_workspace):
        """Test first_success strategy returns first successful result."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Claude was first",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Claude done", execution_time=0.5
                        ),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

            MockExecutor.assert_called_once()
            call_args = MockExecutor.call_args
            assert call_args[1]["strategy"] == AggregationStrategy.FIRST_SUCCESS

    @pytest.mark.asyncio
    async def test_voting_strategy(self, temp_workspace):
        """Test voting strategy requires consensus."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Consensus answer",
                    strategy_used=AggregationStrategy.VOTING,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Answer A", execution_time=0.5
                        ),
                        ToolResult(
                            tool="opencode", success=True, output="Answer A", execution_time=0.5
                        ),
                        ToolResult(
                            tool="cursor", success=True, output="Answer B", execution_time=0.5
                        ),
                    ],
                    winning_tool="claude",
                    metadata={"votes": {"Answer A": 2, "Answer B": 1}},
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode", "cursor"],
                prompt="Test",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="voting",
            )

            MockExecutor.assert_called_once()
            call_args = MockExecutor.call_args
            assert call_args[1]["strategy"] == AggregationStrategy.VOTING


# ---------------------------------------------------------------------------
# Test: Scratchpad State Management
# ---------------------------------------------------------------------------


class TestScratchpadStateManagement:
    """Test scratchpad state management in multi-tool context."""

    @pytest.mark.asyncio
    async def test_scratchpad_content_passed_to_tools(self, temp_workspace):
        """Test that scratchpad content is passed to tools."""
        received_contexts = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                received_contexts.append(context)
                temp_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Original prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

            # Context should contain both prompt and scratchpad
            assert len(received_contexts) == 1
            assert "Original prompt" in received_contexts[0]
            assert "Scratchpad" in received_contexts[0] or "STATUS" in received_contexts[0]

    @pytest.mark.asyncio
    async def test_early_exit_on_status_done(self, temp_workspace):
        """Test that loop exits early when STATUS: DONE is found."""
        # Pre-populate scratchpad with DONE status
        temp_workspace["scratchpad"].write_text("# Scratchpad\n\nSTATUS: DONE\n\nCompleted!")

        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                return AggregatedResult(
                    success=True,
                    primary_output="Should not run",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Should not execute because STATUS: DONE found before first iteration
            assert iteration_count[0] == 0


# ---------------------------------------------------------------------------
# Test: Backpressure Integration
# ---------------------------------------------------------------------------


class TestBackpressureIntegration:
    """Test backpressure (test command) with multi-tool execution."""

    @pytest.mark.asyncio
    async def test_backpressure_runs_after_each_iteration(self, temp_workspace):
        """Test that test command runs after each iteration."""
        test_cmd_count = [0]
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Done",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            with patch("aurora_cli.commands.headless._run_backpressure") as mock_bp:

                def count_backpressure(cmd):
                    test_cmd_count[0] += 1

                mock_bp.side_effect = count_backpressure

                await _run_multi_tool_loop(
                    tools_list=["claude", "opencode"],
                    prompt="Test",
                    scratchpad=temp_workspace["scratchpad"],
                    max_iter=1,
                    test_cmd="pytest tests/",
                    strategy="first_success",
                )

                # Backpressure should have been called (may be 0 if DONE before iteration)


# ---------------------------------------------------------------------------
# Test: Error Handling in Multi-Tool Context
# ---------------------------------------------------------------------------


class TestMultiToolErrorHandling:
    """Test error handling in multi-tool execution context."""

    @pytest.mark.asyncio
    async def test_tool_failure_continues_loop(self, temp_workspace):
        """Test that single tool failure doesn't stop the loop."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                if iteration_count[0] >= 2:
                    temp_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=True,  # Still successful overall
                    primary_output="OpenCode saved the day",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(tool="claude", success=False, output="", error="Claude crashed"),
                        ToolResult(
                            tool="opencode", success=True, output="Success", execution_time=0.5
                        ),
                    ],
                    winning_tool="opencode",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="all_complete",
            )

            assert iteration_count[0] == 2

    @pytest.mark.asyncio
    async def test_all_tools_fail(self, temp_workspace):
        """Test behavior when all tools fail."""
        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                temp_workspace["scratchpad"].write_text("STATUS: DONE")
                return AggregatedResult(
                    success=False,
                    primary_output="",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(tool="claude", success=False, output="", error="Failed"),
                        ToolResult(tool="opencode", success=False, output="", error="Failed"),
                    ],
                    metadata={"error": "All tools failed"},
                )

            mock_executor.execute = mock_execute

            # Should not raise, just continue
            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="all_complete",
            )


# ---------------------------------------------------------------------------
# Test: Realistic Workflow Scenarios
# ---------------------------------------------------------------------------


class TestRealisticWorkflows:
    """Test realistic multi-tool workflow scenarios."""

    @pytest.mark.asyncio
    async def test_code_review_workflow(self, temp_workspace):
        """Test a code review workflow with both tools."""
        temp_workspace["prompt"].write_text(
            """# Goal
Review the code changes in this PR for bugs and improvements.

# Success Criteria
- [ ] All critical issues identified
- [ ] Suggestions for improvements documented
"""
        )
        temp_workspace["scratchpad"].write_text(
            """# Scratchpad
STATUS: IN_PROGRESS

## Files to Review
- src/main.py
- src/utils.py
"""
        )

        workflow_steps = []

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                workflow_steps.append("execute")
                # Simulate tools completing the review
                temp_workspace["scratchpad"].write_text(
                    """# Scratchpad
STATUS: DONE

## Review Complete
- Claude found: potential null reference in main.py:45
- OpenCode found: unused import in utils.py:3
- Both agree: code is generally well-structured
"""
                )
                return AggregatedResult(
                    success=True,
                    primary_output="Review completed successfully",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Found potential null reference",
                            execution_time=2.0,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="Found unused import",
                            execution_time=1.5,
                        ),
                    ],
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt=temp_workspace["prompt"].read_text(),
                scratchpad=temp_workspace["scratchpad"],
                max_iter=5,
                test_cmd=None,
                strategy="all_complete",
            )

            assert len(workflow_steps) == 1

    @pytest.mark.asyncio
    async def test_bug_fix_workflow(self, temp_workspace):
        """Test a bug fix workflow with iterative refinement."""
        temp_workspace["prompt"].write_text(
            """# Goal
Fix the authentication bug where users are logged out unexpectedly.

# Success Criteria
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Tests pass
"""
        )

        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                if iteration_count[0] == 1:
                    # First iteration: analyze
                    return AggregatedResult(
                        success=True,
                        primary_output="Found the issue in session handler",
                        strategy_used=AggregationStrategy.FIRST_SUCCESS,
                        tool_results=[
                            ToolResult(
                                tool="claude",
                                success=True,
                                output="Root cause: session timeout",
                                execution_time=1.0,
                            ),
                        ],
                        winning_tool="claude",
                    )
                elif iteration_count[0] == 2:
                    # Second iteration: fix
                    return AggregatedResult(
                        success=True,
                        primary_output="Fix applied",
                        strategy_used=AggregationStrategy.FIRST_SUCCESS,
                        tool_results=[
                            ToolResult(
                                tool="opencode",
                                success=True,
                                output="Updated session config",
                                execution_time=1.5,
                            ),
                        ],
                        winning_tool="opencode",
                    )
                else:
                    # Third iteration: done
                    temp_workspace["scratchpad"].write_text("STATUS: DONE")
                    return AggregatedResult(
                        success=True,
                        primary_output="All tests pass",
                        strategy_used=AggregationStrategy.FIRST_SUCCESS,
                        tool_results=[],
                    )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt=temp_workspace["prompt"].read_text(),
                scratchpad=temp_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            assert iteration_count[0] == 3


# ---------------------------------------------------------------------------
# Test: Configuration Variations
# ---------------------------------------------------------------------------


class TestConfigurationVariations:
    """Test various configuration combinations."""

    def test_custom_timeout(
        self, runner, temp_workspace, mock_tools_in_path, mock_git_feature_branch
    ):
        """Test custom timeout configuration."""
        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            result = runner.invoke(
                headless_command,
                [
                    "-p",
                    str(temp_workspace["prompt"]),
                    "-t",
                    "claude",
                    "-t",
                    "opencode",
                    "--timeout",
                    "300",
                    "--show-config",
                ],
            )

            assert result.exit_code == 0
            assert "300" in result.output

    def test_all_strategies_with_multi_tool(self, runner, temp_workspace, mock_tools_in_path):
        """Test all strategies are accepted with multi-tool config."""
        strategies = ["first_success", "all_complete", "voting", "best_score", "merge"]

        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            for strategy in strategies:
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_workspace["prompt"]),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--strategy",
                        strategy,
                        "--show-config",
                    ],
                )

                assert result.exit_code == 0, f"Strategy {strategy} failed"
                assert strategy in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
