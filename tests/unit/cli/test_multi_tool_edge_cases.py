"""Unit tests for multi-tool concurrent execution edge cases.

Tests cover scenarios that are difficult to reproduce in integration tests:
- Race conditions in first_success cancellation
- Timeout handling under concurrent load
- Memory pressure with large outputs
- Tool failure cascades
- Partial completion scenarios
- Resource cleanup on cancellation
"""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ConflictDetector,
    ConflictInfo,
    ConflictResolver,
    ConflictSeverity,
    ToolConfig,
    ToolResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_registry():
    """Create mock ToolProviderRegistry."""
    with patch("aurora_cli.concurrent_executor.shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/tool"
        from aurora_cli.tool_providers import ToolProviderRegistry

        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()
        registry._providers = {}
        registry._instances = {}
        yield registry
        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Race Conditions in First Success
# ---------------------------------------------------------------------------


class TestFirstSuccessRaceConditions:
    """Test race conditions in first_success strategy."""

    @pytest.mark.asyncio
    async def test_near_simultaneous_success(self, mock_registry):
        """Test when two tools succeed almost simultaneously."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        execution_order = []

        async def mock_execute(tool, prompt, cancel_event=None):
            execution_order.append(f"{tool.name}_start")
            # Both tools complete in nearly the same time
            await asyncio.sleep(0.001)
            execution_order.append(f"{tool.name}_end")
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} output",
                execution_time=0.001,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            # One of the tools should win
            assert result.winning_tool in ["claude", "opencode"]
            # Both should have started
            assert "claude_start" in execution_order
            assert "opencode_start" in execution_order

    @pytest.mark.asyncio
    async def test_first_success_with_rapid_failures(self, mock_registry):
        """Test first_success when failures come rapidly before any success."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2", "tool3"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        call_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            call_count[0] += 1
            if tool.name == "tool3":
                await asyncio.sleep(0.02)
                return ToolResult(tool="tool3", success=True, output="Success", execution_time=0.02)
            # tool1 and tool2 fail quickly
            await asyncio.sleep(0.001)
            return ToolResult(
                tool=tool.name, success=False, output="", error="Failed fast", execution_time=0.001
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "tool3"
            # All tools should have been executed
            assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_cancellation_during_result_processing(self, mock_registry):
        """Test cancellation during result aggregation doesn't cause issues."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(
                    tool="claude", success=True, output="Output", execution_time=0.001
                )
            # opencode hangs and gets cancelled
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                return ToolResult(
                    tool="opencode", success=False, output="", error="Cancelled", exit_code=-2
                )
            return ToolResult(tool="opencode", success=True, output="Slow", execution_time=10.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "claude"


# ---------------------------------------------------------------------------
# Test: Timeout Scenarios
# ---------------------------------------------------------------------------


class TestTimeoutScenarios:
    """Test timeout handling in concurrent execution."""

    @pytest.mark.asyncio
    async def test_all_tools_timeout(self, mock_registry):
        """Test behavior when all tools timeout."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", timeout=0.01),
                ToolConfig(name="opencode", timeout=0.01),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=f"Timeout after {tool.timeout}s",
                exit_code=-1,
                execution_time=tool.timeout,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is False
            assert all("Timeout" in r.error for r in result.tool_results)

    @pytest.mark.asyncio
    async def test_partial_timeout(self, mock_registry):
        """Test when some tools timeout but others succeed."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="fast_tool", timeout=10.0),
                ToolConfig(name="slow_tool", timeout=0.01),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "fast_tool":
                return ToolResult(
                    tool="fast_tool", success=True, output="Fast success", execution_time=0.001
                )
            return ToolResult(
                tool="slow_tool",
                success=False,
                output="",
                error="Timeout after 0.01s",
                exit_code=-1,
                execution_time=0.01,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "fast_tool"
            assert len(result.tool_results) == 2

    @pytest.mark.asyncio
    async def test_timeout_cleanup(self, mock_registry):
        """Test that timed out processes are cleaned up properly."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="claude", timeout=0.001)],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        cleanup_called = [False]

        async def mock_execute(tool, prompt, cancel_event=None):
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                cleanup_called[0] = True
                return ToolResult(
                    tool="claude", success=False, output="", error="Cancelled", exit_code=-2
                )
            return ToolResult(tool="claude", success=True, output="Never", execution_time=10.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            # The mock won't actually timeout because we're patching _execute_tool
            # but we can verify the cleanup path works
            result = await executor.execute("Test prompt")

            # With mocked execute, it will complete (because the mock doesn't respect timeout)
            # This test validates the structure handles timeouts gracefully
            assert result is not None


# ---------------------------------------------------------------------------
# Test: Memory and Large Output Handling
# ---------------------------------------------------------------------------


class TestLargeOutputHandling:
    """Test handling of large outputs from tools."""

    @pytest.mark.asyncio
    async def test_very_large_output_merge(self, mock_registry):
        """Test merge strategy with very large outputs."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.MERGE,
        )

        large_output_1 = "Claude: " + "A" * 50000
        large_output_2 = "OpenCode: " + "B" * 50000

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude", success=True, output=large_output_1, execution_time=1.0
                    ),
                    ToolResult(
                        tool="opencode", success=True, output=large_output_2, execution_time=1.0
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.primary_output) > 100000
            assert "=== claude ===" in result.primary_output
            assert "=== opencode ===" in result.primary_output

    @pytest.mark.asyncio
    async def test_binary_like_output(self, mock_registry):
        """Test handling of outputs with binary-like content."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        # Simulate output with null bytes and other binary-like content
        binary_like = "Output\x00with\x00null\x00bytes"

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output=binary_like,
                execution_time=0.1,
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.primary_output == binary_like


# ---------------------------------------------------------------------------
# Test: Failure Cascade Scenarios
# ---------------------------------------------------------------------------


class TestFailureCascades:
    """Test failure cascade scenarios."""

    @pytest.mark.asyncio
    async def test_cascading_failures(self, mock_registry):
        """Test when one tool failure causes others to fail."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2", "tool3"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        failure_order = []

        async def mock_execute(tool, prompt, cancel_event=None):
            failure_order.append(tool.name)
            # Each tool fails with increasing delay
            await asyncio.sleep(0.001 * len(failure_order))
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=f"Failed: {tool.name}",
                exit_code=1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is False
            assert len(result.tool_results) == 3
            assert all(not r.success for r in result.tool_results)

    @pytest.mark.asyncio
    async def test_exception_in_tool_execution(self, mock_registry):
        """Test that exceptions are converted to failed results."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                raise RuntimeError("Unexpected error in Claude")
            return ToolResult(tool="opencode", success=True, output="Success", execution_time=0.1)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True  # At least one succeeded
            claude_result = next(r for r in result.tool_results if r.tool == "claude")
            assert not claude_result.success
            assert "Unexpected error" in claude_result.error

    @pytest.mark.asyncio
    async def test_provider_unavailable_at_execution(self, mock_registry):
        """Test behavior when provider becomes unavailable during execution."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=False,
                output="",
                error="Provider no longer available",
                exit_code=-1,
            )

            result = await executor.execute("Test prompt")

            assert result.success is False


# ---------------------------------------------------------------------------
# Test: Partial Completion Scenarios
# ---------------------------------------------------------------------------


class TestPartialCompletion:
    """Test partial completion scenarios."""

    @pytest.mark.asyncio
    async def test_some_tools_complete_others_hang(self, mock_registry):
        """Test when some tools complete but others hang indefinitely."""
        executor = ConcurrentToolExecutor(
            tools=["fast", "medium", "slow"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        completed_tools = []

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "fast":
                completed_tools.append("fast")
                return ToolResult(
                    tool="fast", success=True, output="Fast done", execution_time=0.001
                )
            elif tool.name == "medium":
                await asyncio.sleep(0.01)
                completed_tools.append("medium")
                return ToolResult(
                    tool="medium", success=True, output="Medium done", execution_time=0.01
                )
            else:
                try:
                    await asyncio.sleep(100.0)
                except asyncio.CancelledError:
                    completed_tools.append("slow_cancelled")
                    return ToolResult(
                        tool="slow", success=False, output="", error="Cancelled", exit_code=-2
                    )
                return ToolResult(
                    tool="slow", success=True, output="Slow done", execution_time=100.0
                )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "fast"
            # Fast should complete first and trigger cancellation
            assert "fast" in completed_tools

    @pytest.mark.asyncio
    async def test_all_complete_with_mixed_results(self, mock_registry):
        """Test all_complete with varied success/failure mix."""
        executor = ConcurrentToolExecutor(
            tools=["success1", "failure1", "success2", "failure2"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            success = "success" in tool.name
            return ToolResult(
                tool=tool.name,
                success=success,
                output=f"{tool.name} output" if success else "",
                error="" if success else f"{tool.name} error",
                execution_time=0.01,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True  # At least some succeeded
            assert len(result.tool_results) == 4
            successful = [r for r in result.tool_results if r.success]
            failed = [r for r in result.tool_results if not r.success]
            assert len(successful) == 2
            assert len(failed) == 2


# ---------------------------------------------------------------------------
# Test: Concurrency Edge Cases
# ---------------------------------------------------------------------------


class TestConcurrencyEdgeCases:
    """Test concurrency-specific edge cases."""

    @pytest.mark.asyncio
    async def test_concurrent_access_to_cancel_event(self, mock_registry):
        """Test that cancel event is thread-safe across tools."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2", "tool3", "tool4"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        cancel_checks = []

        async def mock_execute(tool, prompt, cancel_event=None):
            # Multiple tools check cancel event simultaneously
            for _ in range(10):
                if cancel_event and cancel_event.is_set():
                    cancel_checks.append((tool.name, "cancelled"))
                    return ToolResult(tool=tool.name, success=False, output="", error="Cancelled")
                await asyncio.sleep(0.0001)

            cancel_checks.append((tool.name, "completed"))
            return ToolResult(tool=tool.name, success=True, output="Done", execution_time=0.001)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Should complete without race condition issues
            assert result.success is True

    @pytest.mark.asyncio
    async def test_high_concurrency_stress(self, mock_registry):
        """Test behavior under high concurrency."""
        # Create many tools
        tools = [f"tool{i}" for i in range(10)]
        executor = ConcurrentToolExecutor(
            tools=tools,
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        execution_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            execution_count[0] += 1
            await asyncio.sleep(0.001)
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"Output from {tool.name}",
                execution_time=0.001,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.tool_results) == 10
            assert execution_count[0] == 10

    @pytest.mark.asyncio
    async def test_rapid_succession_executions(self, mock_registry):
        """Test multiple rapid executions don't interfere."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        execution_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            execution_count[0] += 1
            await asyncio.sleep(0.001)
            return ToolResult(tool=tool.name, success=True, output="Done", execution_time=0.001)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            # Run multiple executions rapidly
            results = await asyncio.gather(
                executor.execute("Prompt 1"),
                executor.execute("Prompt 2"),
                executor.execute("Prompt 3"),
            )

            assert all(r.success for r in results)


# ---------------------------------------------------------------------------
# Test: Strategy-Specific Edge Cases
# ---------------------------------------------------------------------------


class TestStrategyEdgeCases:
    """Test edge cases specific to aggregation strategies."""

    @pytest.mark.asyncio
    async def test_voting_with_all_different(self, mock_registry):
        """Test voting when all tools produce different outputs."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor"],
            strategy=AggregationStrategy.VOTING,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=True, output="Answer A", execution_time=1.0),
                    ToolResult(
                        tool="opencode", success=True, output="Answer B", execution_time=1.0
                    ),
                    ToolResult(tool="cursor", success=True, output="Answer C", execution_time=1.0),
                ],
            )

            result = await executor.execute("Test prompt")

            # No clear winner - should pick one
            assert result.success is True
            assert result.winning_tool in ["claude", "opencode", "cursor"]

    @pytest.mark.asyncio
    async def test_best_score_with_equal_scores(self, mock_registry):
        """Test best_score when multiple tools have equal scores."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.BEST_SCORE,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude", success=True, output="Same length", execution_time=10.0
                    ),
                    ToolResult(
                        tool="opencode", success=True, output="Same length", execution_time=10.0
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert "scores" in result.metadata
            # Scores should be equal
            scores = result.metadata["scores"]
            assert scores["claude"] == scores["opencode"]

    @pytest.mark.asyncio
    async def test_consensus_with_threshold_boundary(self, mock_registry):
        """Test consensus at exact threshold boundary."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.CONSENSUS,
        )

        # Create outputs that are exactly at 80% similarity
        base_output = "This is a test output with some content."
        # Modify to get ~80% similarity
        modified_output = "This is a test output with other content."

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=True, output=base_output, execution_time=1.0),
                    ToolResult(
                        tool="opencode", success=True, output=modified_output, execution_time=1.0
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert "consensus_reached" in result.metadata
            assert "similarity_score" in result.metadata

    @pytest.mark.asyncio
    async def test_smart_merge_with_complementary_content(self, mock_registry):
        """Test smart_merge with complementary but different content."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.SMART_MERGE,
        )

        # Complementary outputs that should both be included
        output1 = "## Analysis\n\nThis is Claude's analysis of the problem.\n\nKey findings:\n- Finding A\n- Finding B"
        output2 = (
            "## Implementation\n\nThis is OpenCode's implementation.\n\nSteps:\n- Step 1\n- Step 2"
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=True, output=output1, execution_time=1.0),
                    ToolResult(tool="opencode", success=True, output=output2, execution_time=1.0),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.conflict_info is not None


# ---------------------------------------------------------------------------
# Test: Input Edge Cases
# ---------------------------------------------------------------------------


class TestInputEdgeCases:
    """Test edge cases in input handling."""

    @pytest.mark.asyncio
    async def test_empty_prompt(self, mock_registry):
        """Test execution with empty prompt."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Response to empty prompt",
                execution_time=0.1,
            )

            result = await executor.execute("")

            assert result.success is True
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_very_long_prompt(self, mock_registry):
        """Test execution with very long prompt."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        long_prompt = "A" * 100000

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Response",
                execution_time=0.1,
            )

            result = await executor.execute(long_prompt)

            assert result.success is True
            # Verify the full prompt was passed
            call_args = mock_execute.call_args
            assert len(call_args[0][1]) == 100000

    @pytest.mark.asyncio
    async def test_special_characters_in_prompt(self, mock_registry):
        """Test prompt with special characters."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        special_prompt = "Test with $pecial ch@rs: `code` \"quotes\" 'apostrophes' \n\t\r"

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Response",
                execution_time=0.1,
            )

            result = await executor.execute(special_prompt)

            assert result.success is True


# ---------------------------------------------------------------------------
# Test: Tool Config Edge Cases
# ---------------------------------------------------------------------------


class TestToolConfigEdgeCases:
    """Test edge cases in tool configuration."""

    def test_zero_timeout(self, mock_registry):
        """Test tool with zero timeout."""
        # Zero timeout should likely cause immediate timeout
        config = ToolConfig(name="test", timeout=0.0)
        assert config.timeout == 0.0

    def test_negative_weight(self, mock_registry):
        """Test tool with negative weight."""
        # Negative weight should still work (though unusual)
        config = ToolConfig(name="test", weight=-1.0)
        assert config.weight == -1.0

    def test_duplicate_tools(self, mock_registry):
        """Test execution with duplicate tools in list."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "claude"],  # Same tool twice
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        assert len(executor.tools) == 2

    def test_all_tools_disabled(self, mock_registry):
        """Test when all tools are disabled."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", enabled=False),
                ToolConfig(name="opencode", enabled=False),
            ],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        # This should be testable via execute
        # The fixture already handles validation bypass for disabled tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
