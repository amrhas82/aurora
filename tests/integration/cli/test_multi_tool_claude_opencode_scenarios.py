"""Integration tests for Claude + OpenCode multi-tool concurrent execution scenarios.

Tests cover realistic workflow scenarios for running Claude and OpenCode
together with various aggregation strategies and configurations.

These tests are designed to validate the complete integration path from
CLI invocation through to result aggregation and conflict resolution.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.headless import (
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
    """Create a temporary workspace with all required files."""
    # Create .aurora/headless directory
    headless_dir = tmp_path / ".aurora" / "headless"
    headless_dir.mkdir(parents=True)

    # Create prompt file
    prompt = headless_dir / "prompt.md"
    prompt.write_text(
        """# Goal
Implement a feature using both Claude and OpenCode.

# Success Criteria
- [ ] Feature is complete
- [ ] Both tools agree on approach
- [ ] Tests pass
"""
    )

    # Create scratchpad
    scratchpad = headless_dir / "scratchpad.md"
    scratchpad.write_text(
        """# Scratchpad

## STATUS: IN_PROGRESS

## Current State
Starting fresh.
"""
    )

    return {
        "root": tmp_path,
        "headless_dir": headless_dir,
        "prompt": prompt,
        "scratchpad": scratchpad,
    }


@pytest.fixture
def mock_claude_opencode_available():
    """Mock Claude and OpenCode as available in PATH."""

    def which_side_effect(cmd):
        if cmd in ("claude", "opencode"):
            return f"/usr/bin/{cmd}"
        return None

    with patch("shutil.which", side_effect=which_side_effect):
        with patch("aurora_cli.commands.headless.shutil.which", side_effect=which_side_effect):
            with patch(
                "aurora_cli.concurrent_executor.shutil.which", side_effect=which_side_effect
            ):
                yield


@pytest.fixture
def mock_git_safe():
    """Mock git to return a safe feature branch."""

    def mock_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        if isinstance(cmd, list) and "git" in cmd[0]:
            result = Mock()
            result.returncode = 0
            result.stdout = "feature-branch\n"
            result.stderr = ""
            return result
        result = Mock()
        result.returncode = 0
        result.stdout = "Output"
        result.stderr = ""
        return result

    with patch("aurora_cli.commands.headless.subprocess.run", side_effect=mock_run):
        with patch("subprocess.run", side_effect=mock_run):
            yield


# ---------------------------------------------------------------------------
# Test: Claude + OpenCode Parallel Execution
# ---------------------------------------------------------------------------


class TestClaudeOpenCodeParallel:
    """Test Claude and OpenCode running in parallel."""

    @pytest.mark.asyncio
    async def test_both_tools_succeed_parallel(self, temp_workspace):
        """Test successful parallel execution with both tools."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Both tools completed successfully",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Claude's implementation complete",
                            execution_time=2.5,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="OpenCode's implementation complete",
                            execution_time=3.0,
                        ),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

            MockExecutor.assert_called_once()
            call_args = MockExecutor.call_args
            assert call_args[0][0] == ["claude", "opencode"]

    @pytest.mark.asyncio
    async def test_claude_faster_than_opencode(self, temp_workspace):
        """Test first_success when Claude finishes first."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Claude's quick response",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Fast Claude", execution_time=1.0
                        ),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

    @pytest.mark.asyncio
    async def test_opencode_faster_than_claude(self, temp_workspace):
        """Test first_success when OpenCode finishes first."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="OpenCode's quick response",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="Fast OpenCode",
                            execution_time=0.8,
                        ),
                        ToolResult(
                            tool="claude", success=True, output="Slower Claude", execution_time=2.0
                        ),
                    ],
                    winning_tool="opencode",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )


# ---------------------------------------------------------------------------
# Test: Conflict Scenarios
# ---------------------------------------------------------------------------


class TestConflictScenarios:
    """Test conflict detection between Claude and OpenCode outputs."""

    @pytest.mark.asyncio
    async def test_tools_disagree_on_approach(self, temp_workspace):
        """Test when Claude and OpenCode suggest different approaches."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Claude's approach using recursion",
                    strategy_used=AggregationStrategy.CONSENSUS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Use recursion for tree traversal",
                            execution_time=2.0,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="Use iteration with a stack for tree traversal",
                            execution_time=2.5,
                        ),
                    ],
                    winning_tool="claude",
                    conflict_info=ConflictInfo(
                        severity=ConflictSeverity.MODERATE,
                        tools_involved=["claude", "opencode"],
                        description="Different algorithmic approaches suggested",
                        similarity_score=0.45,
                    ),
                    metadata={
                        "consensus_reached": False,
                        "resolution_method": "weighted_vote",
                    },
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="consensus",
            )

    @pytest.mark.asyncio
    async def test_tools_agree_on_approach(self, temp_workspace):
        """Test when both tools agree on the approach."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Consistent approach from both",
                    strategy_used=AggregationStrategy.CONSENSUS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Implement using the repository pattern",
                            execution_time=2.0,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="Implement using the repository pattern",
                            execution_time=2.2,
                        ),
                    ],
                    winning_tool="claude",
                    conflict_info=ConflictInfo(
                        severity=ConflictSeverity.NONE,
                        tools_involved=["claude", "opencode"],
                        description="Tools agree",
                        similarity_score=0.98,
                    ),
                    metadata={
                        "consensus_reached": True,
                        "similarity_score": 0.98,
                    },
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="consensus",
            )

    @pytest.mark.asyncio
    async def test_smart_merge_complementary_outputs(self, temp_workspace):
        """Test smart_merge with complementary Claude and OpenCode outputs."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="# Merged Output\n\n## Claude Analysis\n...\n\n## OpenCode Implementation\n...",
                    strategy_used=AggregationStrategy.SMART_MERGE,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="## Analysis\nDeep analysis of the problem space.",
                            execution_time=3.0,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="## Implementation\nConcrete code implementation.",
                            execution_time=2.5,
                        ),
                    ],
                    conflict_info=ConflictInfo(
                        severity=ConflictSeverity.MODERATE,
                        tools_involved=["claude", "opencode"],
                        description="Complementary content merged",
                        similarity_score=0.35,
                    ),
                    metadata={
                        "merged_count": 2,
                        "conflict_severity": "moderate",
                    },
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="smart_merge",
            )


# ---------------------------------------------------------------------------
# Test: Failure Recovery Scenarios
# ---------------------------------------------------------------------------


class TestFailureRecoveryScenarios:
    """Test failure recovery when one tool fails."""

    @pytest.mark.asyncio
    async def test_claude_fails_opencode_succeeds(self, temp_workspace):
        """Test recovery when Claude fails but OpenCode succeeds."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="OpenCode saved the day",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=False,
                            output="",
                            error="Rate limit exceeded",
                            exit_code=1,
                            execution_time=0.5,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="OpenCode completed the task",
                            execution_time=3.0,
                        ),
                    ],
                    winning_tool="opencode",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

    @pytest.mark.asyncio
    async def test_opencode_fails_claude_succeeds(self, temp_workspace):
        """Test recovery when OpenCode fails but Claude succeeds."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=True,
                    primary_output="Claude to the rescue",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=True,
                            output="Claude completed the task",
                            execution_time=2.0,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=False,
                            output="",
                            error="Connection timeout",
                            exit_code=1,
                            execution_time=30.0,
                        ),
                    ],
                    winning_tool="claude",
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="first_success",
            )

    @pytest.mark.asyncio
    async def test_both_tools_fail(self, temp_workspace):
        """Test behavior when both Claude and OpenCode fail."""
        temp_workspace["scratchpad"].write_text("STATUS: DONE")

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                return AggregatedResult(
                    success=False,
                    primary_output="",
                    strategy_used=AggregationStrategy.ALL_COMPLETE,
                    tool_results=[
                        ToolResult(
                            tool="claude",
                            success=False,
                            output="",
                            error="API error",
                            exit_code=1,
                            execution_time=0.5,
                        ),
                        ToolResult(
                            tool="opencode",
                            success=False,
                            output="",
                            error="Service unavailable",
                            exit_code=1,
                            execution_time=0.8,
                        ),
                    ],
                    metadata={"error": "All tools failed"},
                )

            mock_executor.execute = mock_execute

            # Should not raise, just log the failure
            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=1,
                test_cmd=None,
                strategy="all_complete",
            )


# ---------------------------------------------------------------------------
# Test: Sequential Round-Robin
# ---------------------------------------------------------------------------


class TestSequentialRoundRobin:
    """Test sequential execution alternating between Claude and OpenCode."""

    def test_alternates_correctly(self, runner, temp_workspace, mock_claude_opencode_available):
        """Test that sequential mode alternates Claude -> OpenCode -> Claude."""
        with patch("pathlib.Path.cwd", return_value=temp_workspace["root"]):
            tool_calls = []

            def mock_subprocess(*args, **kwargs):
                cmd = args[0] if args else []
                if isinstance(cmd, list):
                    if "git" in cmd[0]:
                        mock = Mock()
                        mock.returncode = 0
                        mock.stdout = "feature-branch\n"
                        return mock
                    tool_calls.append(cmd[0])
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
                            "6",
                        ],
                    )

                    # Should alternate: claude, opencode, claude, opencode, claude, opencode
                    assert tool_calls == [
                        "claude",
                        "opencode",
                        "claude",
                        "opencode",
                        "claude",
                        "opencode",
                    ]


# ---------------------------------------------------------------------------
# Test: Multi-Iteration Scenarios
# ---------------------------------------------------------------------------


class TestMultiIterationScenarios:
    """Test multi-iteration workflows with Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_iterative_refinement(self, temp_workspace):
        """Test iterative refinement with both tools over multiple iterations."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                if iteration_count[0] == 1:
                    return AggregatedResult(
                        success=True,
                        primary_output="Draft implementation",
                        strategy_used=AggregationStrategy.ALL_COMPLETE,
                        tool_results=[
                            ToolResult(
                                tool="claude",
                                success=True,
                                output="Draft by Claude",
                                execution_time=2.0,
                            ),
                            ToolResult(
                                tool="opencode",
                                success=True,
                                output="Draft by OpenCode",
                                execution_time=2.5,
                            ),
                        ],
                    )
                elif iteration_count[0] == 2:
                    return AggregatedResult(
                        success=True,
                        primary_output="Refined implementation",
                        strategy_used=AggregationStrategy.ALL_COMPLETE,
                        tool_results=[
                            ToolResult(
                                tool="claude",
                                success=True,
                                output="Refined by Claude",
                                execution_time=1.5,
                            ),
                            ToolResult(
                                tool="opencode",
                                success=True,
                                output="Refined by OpenCode",
                                execution_time=2.0,
                            ),
                        ],
                    )
                else:
                    temp_workspace["scratchpad"].write_text("STATUS: DONE")
                    return AggregatedResult(
                        success=True,
                        primary_output="Final implementation",
                        strategy_used=AggregationStrategy.ALL_COMPLETE,
                        tool_results=[
                            ToolResult(
                                tool="claude",
                                success=True,
                                output="Final by Claude",
                                execution_time=1.0,
                            ),
                            ToolResult(
                                tool="opencode",
                                success=True,
                                output="Final by OpenCode",
                                execution_time=1.2,
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
    async def test_convergence_over_iterations(self, temp_workspace):
        """Test that tools converge on agreement over multiple iterations."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                # Simulate increasing agreement
                similarity = 0.4 + (iteration_count[0] * 0.2)
                if similarity >= 0.95:
                    temp_workspace["scratchpad"].write_text("STATUS: DONE")

                severity = (
                    ConflictSeverity.MAJOR
                    if similarity < 0.6
                    else (ConflictSeverity.MODERATE if similarity < 0.8 else ConflictSeverity.NONE)
                )

                return AggregatedResult(
                    success=True,
                    primary_output=f"Iteration {iteration_count[0]} output",
                    strategy_used=AggregationStrategy.CONSENSUS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Claude output", execution_time=1.0
                        ),
                        ToolResult(
                            tool="opencode",
                            success=True,
                            output="OpenCode output",
                            execution_time=1.0,
                        ),
                    ],
                    conflict_info=ConflictInfo(
                        severity=severity,
                        tools_involved=["claude", "opencode"],
                        description=f"Similarity: {similarity:.0%}",
                        similarity_score=similarity,
                    ),
                    metadata={"consensus_reached": similarity >= 0.8},
                )

            mock_executor.execute = mock_execute

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=10,
                test_cmd=None,
                strategy="consensus",
            )

            # Should converge within a few iterations
            assert iteration_count[0] <= 4


# ---------------------------------------------------------------------------
# Test: Budget and Time Limit
# ---------------------------------------------------------------------------


class TestBudgetAndTimeLimit:
    """Test budget and time limit enforcement with Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_time_limit_stops_execution(self, temp_workspace):
        """Test that time limit stops execution."""
        iteration_count = [0]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            async def mock_execute(context):
                iteration_count[0] += 1
                return AggregatedResult(
                    success=True,
                    primary_output="Still working",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[
                        ToolResult(
                            tool="claude", success=True, output="Progress", execution_time=1.0
                        ),
                    ],
                )

            mock_executor.execute = mock_execute

            # Set a very short time limit
            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=temp_workspace["scratchpad"],
                max_iter=100,
                test_cmd=None,
                strategy="first_success",
                time_limit=0,  # Immediate stop
            )

            # Should stop immediately due to time limit
            assert iteration_count[0] == 0


# ---------------------------------------------------------------------------
# Test: Results Display
# ---------------------------------------------------------------------------


class TestResultsDisplay:
    """Test results display for Claude + OpenCode scenarios."""

    def test_display_with_conflict_info(self, capsys):
        """Test display of results with conflict information."""
        result = AggregatedResult(
            success=True,
            primary_output="Merged output",
            strategy_used=AggregationStrategy.SMART_MERGE,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Claude did X", execution_time=2.0),
                ToolResult(
                    tool="opencode", success=True, output="OpenCode did Y", execution_time=2.5
                ),
            ],
            conflict_info=ConflictInfo(
                severity=ConflictSeverity.MODERATE,
                tools_involved=["claude", "opencode"],
                description="Different approaches suggested",
                similarity_score=0.55,
                conflicting_sections=[
                    {
                        "type": "code_blocks",
                        "tool1": "claude",
                        "tool2": "opencode",
                        "count1": 2,
                        "count2": 3,
                    }
                ],
            ),
            metadata={
                "merged_count": 2,
                "conflict_severity": "moderate",
                "similarity_score": 0.55,
            },
        )

        # Should not raise
        _display_multi_tool_results(result, "smart_merge")

    def test_display_consensus_not_reached(self, capsys):
        """Test display when consensus is not reached."""
        result = AggregatedResult(
            success=True,
            primary_output="Winner's output",
            strategy_used=AggregationStrategy.CONSENSUS,
            tool_results=[
                ToolResult(tool="claude", success=True, output="Yes", execution_time=1.0),
                ToolResult(tool="opencode", success=True, output="No", execution_time=1.0),
            ],
            winning_tool="claude",
            conflict_info=ConflictInfo(
                severity=ConflictSeverity.MAJOR,
                tools_involved=["claude", "opencode"],
                description="Significant disagreement",
                similarity_score=0.15,
            ),
            metadata={
                "consensus_reached": False,
                "threshold": 0.8,
                "resolution_method": "weighted_vote",
            },
        )

        _display_multi_tool_results(result, "consensus")


# ---------------------------------------------------------------------------
# Test: CLI Integration
# ---------------------------------------------------------------------------


class TestCLIIntegration:
    """Test CLI integration for Claude + OpenCode scenarios."""

    def test_cli_parallel_invocation(
        self, runner, temp_workspace, mock_claude_opencode_available, mock_git_safe
    ):
        """Test CLI correctly invokes parallel execution."""
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

                mock_asyncio.assert_called_once()
                # Check the output mentions both tools
                assert "claude" in result.output.lower()
                assert "opencode" in result.output.lower()

    def test_cli_strategy_options(self, runner, temp_workspace, mock_claude_opencode_available):
        """Test that all strategies can be specified via CLI."""
        strategies = [
            "first_success",
            "all_complete",
            "voting",
            "best_score",
            "merge",
            "smart_merge",
            "consensus",
        ]

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

                assert result.exit_code == 0, f"Strategy {strategy} failed: {result.output}"
                assert strategy in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
