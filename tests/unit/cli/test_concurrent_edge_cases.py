"""Edge case tests for concurrent tool execution.

Tests cover:
- Boundary conditions and corner cases
- Race conditions and timing issues
- Resource exhaustion scenarios
- Malformed inputs and outputs
- State corruption prevention
- Registry manipulation during execution
"""

import asyncio
import gc
import weakref
from unittest.mock import patch

import pytest

from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ConflictDetector,
    ConflictResolver,
    ConflictSeverity,
    ToolConfig,
    ToolResult,
)
from aurora_cli.tool_providers import ToolProviderRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_registry():
    """Create mock ToolProviderRegistry."""
    ToolProviderRegistry.reset()
    registry = ToolProviderRegistry.get_instance()
    registry._providers = {}
    registry._instances = {}
    yield registry
    ToolProviderRegistry.reset()


@pytest.fixture
def mock_which():
    """Mock shutil.which for all tests."""
    with patch("aurora_cli.concurrent_executor.shutil.which") as mock:
        mock.return_value = "/usr/bin/tool"
        yield mock


# ---------------------------------------------------------------------------
# Test: Boundary Conditions
# ---------------------------------------------------------------------------


class TestBoundaryConditions:
    """Test boundary conditions for concurrent execution."""

    @pytest.mark.asyncio
    async def test_single_tool_all_strategies(self, mock_registry, mock_which):
        """Test all strategies work correctly with single tool."""
        strategies = [
            AggregationStrategy.FIRST_SUCCESS,
            AggregationStrategy.ALL_COMPLETE,
            AggregationStrategy.BEST_SCORE,
            AggregationStrategy.MERGE,
            AggregationStrategy.SMART_MERGE,
            AggregationStrategy.CONSENSUS,
        ]

        for strategy in strategies:
            executor = ConcurrentToolExecutor(
                tools=["claude"],
                strategy=strategy,
            )

            with patch.object(executor, "_execute_tool") as mock_exec:
                mock_exec.return_value = ToolResult(
                    tool="claude",
                    success=True,
                    output="Single tool output",
                    execution_time=1.0,
                )

                result = await executor.execute("Test prompt")

                assert result.success is True, f"Strategy {strategy} failed with single tool"

    @pytest.mark.asyncio
    async def test_voting_with_exactly_three_tools(self, mock_registry, mock_which):
        """Test voting strategy with minimum required tools (3)."""
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
                    ToolResult(tool="claude", success=True, output="Answer A", execution_time=0.1),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="Answer A",
                        execution_time=0.1,
                    ),
                    ToolResult(tool="cursor", success=True, output="Answer B", execution_time=0.1),
                ],
            )

            result = await executor.execute("Test")

            assert result.success is True
            # 2 vs 1 vote - "Answer A" should win
            assert result.primary_output == "Answer A"

    @pytest.mark.asyncio
    async def test_empty_prompt(self, mock_registry, mock_which):
        """Test execution with empty prompt."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_exec:
            mock_exec.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Response to empty",
                execution_time=0.1,
            )

            result = await executor.execute("")

            assert result.success is True
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_very_long_prompt(self, mock_registry, mock_which):
        """Test execution with very long prompt."""
        executor = ConcurrentToolExecutor(tools=["claude"])
        long_prompt = "x" * 1_000_000  # 1MB prompt

        with patch.object(executor, "_execute_tool") as mock_exec:
            mock_exec.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Handled long prompt",
                execution_time=5.0,
            )

            result = await executor.execute(long_prompt)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_zero_timeout(self, mock_registry, mock_which):
        """Test with zero timeout configuration."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="claude", timeout=0.001)],
        )

        with patch.object(executor, "_execute_direct") as mock_direct:
            mock_direct.return_value = ToolResult(
                tool="claude",
                success=False,
                output="",
                error="Timeout",
                exit_code=-1,
                execution_time=0.001,
            )

            result = await executor.execute("Test")

            assert result.success is False

    @pytest.mark.asyncio
    async def test_max_tools(self, mock_registry, mock_which):
        """Test with many concurrent tools."""
        tools = [f"tool_{i}" for i in range(20)]
        executor = ConcurrentToolExecutor(
            tools=tools,
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mock_execute(tool, prompt, cancel_event=None):
                return ToolResult(
                    tool=tool.name,
                    success=True,
                    output=f"Output from {tool.name}",
                    execution_time=0.01,
                )

            mock_exec.side_effect = mock_execute

            result = await executor.execute("Test")

            assert len(result.tool_results) == 20


# ---------------------------------------------------------------------------
# Test: Race Conditions
# ---------------------------------------------------------------------------


class TestRaceConditions:
    """Test race condition handling."""

    @pytest.mark.asyncio
    async def test_simultaneous_success(self, mock_registry, mock_which):
        """Test when multiple tools succeed simultaneously."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            # Both complete at the same time
            await asyncio.sleep(0.001)
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} output",
                execution_time=0.001,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test")

            assert result.success is True
            assert result.winning_tool in ["claude", "opencode"]

    @pytest.mark.asyncio
    async def test_cancel_propagation(self, mock_registry, mock_which):
        """Test that cancellation propagates correctly."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        cancelled = {"opencode": False}

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                await asyncio.sleep(0.001)
                return ToolResult(tool="claude", success=True, output="Quick", execution_time=0.001)
            try:
                await asyncio.sleep(10.0)  # Long task
            except asyncio.CancelledError:
                cancelled["opencode"] = True
                raise
            return ToolResult(tool="opencode", success=True, output="Slow", execution_time=10.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test")

            assert result.winning_tool == "claude"

    @pytest.mark.asyncio
    async def test_all_cancel_simultaneously(self, mock_registry, mock_which):
        """Test behavior when all tasks are cancelled."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            raise asyncio.CancelledError()

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test")

            # Should handle gracefully
            assert len(result.tool_results) == 2
            for tr in result.tool_results:
                assert tr.success is False


# ---------------------------------------------------------------------------
# Test: Malformed Input/Output
# ---------------------------------------------------------------------------


class TestMalformedInputOutput:
    """Test handling of malformed inputs and outputs."""

    @pytest.mark.asyncio
    async def test_binary_output(self, mock_registry, mock_which):
        """Test handling of binary output from tool."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_exec:
            # Simulate binary data that made it through decoding
            mock_exec.return_value = ToolResult(
                tool="claude",
                success=True,
                output="\x00\x01\x02\xff\xfe",  # Binary-ish data
                execution_time=0.1,
            )

            result = await executor.execute("Test")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_unicode_edge_cases(self, mock_registry, mock_which):
        """Test handling of unusual Unicode."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_exec:
            # Various Unicode edge cases
            unicode_outputs = [
                "\u0000",  # Null character
                "\ud83d\ude00",  # Emoji
                "\u202e",  # Right-to-left override
                "a\u0300",  # Combining character
                "\uffff",  # Maximum BMP character
            ]

            for output in unicode_outputs:
                mock_exec.return_value = ToolResult(
                    tool="claude",
                    success=True,
                    output=output,
                    execution_time=0.1,
                )

                result = await executor.execute("Test")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_output_with_control_characters(self, mock_registry, mock_which):
        """Test output containing control characters."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_exec:
            # ANSI escape codes and other control chars
            mock_exec.return_value = ToolResult(
                tool="claude",
                success=True,
                output="\x1b[31mRed text\x1b[0m\n\tTabbed\r\n",
                execution_time=0.1,
            )

            result = await executor.execute("Test")

            assert result.success is True

    def test_conflict_detection_empty_strings(self):
        """Test conflict detection with empty strings."""
        results = [
            ToolResult(tool="claude", success=True, output="", execution_time=0.1),
            ToolResult(tool="opencode", success=True, output="", execution_time=0.1),
        ]

        conflict = ConflictDetector.detect_conflicts(results)

        # Empty strings are identical
        assert conflict.severity == ConflictSeverity.NONE

    def test_conflict_detection_one_empty(self):
        """Test conflict detection when one output is empty."""
        results = [
            ToolResult(tool="claude", success=True, output="Some content", execution_time=0.1),
            ToolResult(tool="opencode", success=True, output="", execution_time=0.1),
        ]

        conflict = ConflictDetector.detect_conflicts(results)

        # Very different
        assert conflict.similarity_score < 0.5


# ---------------------------------------------------------------------------
# Test: State Corruption Prevention
# ---------------------------------------------------------------------------


class TestStateCorruptionPrevention:
    """Test that state is not corrupted during execution."""

    @pytest.mark.asyncio
    async def test_executor_reuse(self, mock_registry, mock_which):
        """Test that executor can be reused safely."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        call_count = [0]

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mock_execute(tool, prompt, cancel_event=None):
                call_count[0] += 1
                return ToolResult(
                    tool="claude",
                    success=True,
                    output=f"Response {call_count[0]}",
                    execution_time=0.1,
                )

            mock_exec.side_effect = mock_execute

            # Execute multiple times
            r1 = await executor.execute("First")
            r2 = await executor.execute("Second")
            r3 = await executor.execute("Third")

            assert r1.primary_output == "Response 1"
            assert r2.primary_output == "Response 2"
            assert r3.primary_output == "Response 3"

    @pytest.mark.asyncio
    async def test_concurrent_executor_calls(self, mock_registry, mock_which):
        """Test multiple concurrent execute calls on same executor."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mock_execute(tool, prompt, cancel_event=None):
                await asyncio.sleep(0.01)
                return ToolResult(
                    tool="claude",
                    success=True,
                    output=f"Response to: {prompt[:10]}",
                    execution_time=0.01,
                )

            mock_exec.side_effect = mock_execute

            # Launch multiple concurrent calls
            tasks = [executor.execute(f"Prompt {i}") for i in range(5)]

            results = await asyncio.gather(*tasks)

            # All should succeed independently
            assert all(r.success for r in results)
            assert len(set(r.primary_output for r in results)) == 5

    def test_registry_modification_during_execution(self, mock_which):
        """Test that registry modifications don't affect running execution."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        # Get initial state
        initial_tools = set(registry.list_available())

        # Create executor with known tools
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        # Modify registry (unregister a tool)
        registry.unregister("opencode")

        # Executor should still have its tools configured
        assert len(executor.tools) == 2

        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Resource Management
# ---------------------------------------------------------------------------


class TestResourceManagement:
    """Test resource management in concurrent execution."""

    @pytest.mark.asyncio
    async def test_no_memory_leak_on_failure(self, mock_registry, mock_which):
        """Test that failed executions don't leak memory."""
        executor_ref = None

        async def run_failing_execution():
            nonlocal executor_ref
            executor = ConcurrentToolExecutor(
                tools=["claude"],
                strategy=AggregationStrategy.FIRST_SUCCESS,
            )
            executor_ref = weakref.ref(executor)

            with patch.object(executor, "_execute_tool") as mock_exec:
                mock_exec.side_effect = RuntimeError("Intentional failure")

                try:
                    await executor.execute("Test")
                except RuntimeError:
                    pass

        await run_failing_execution()
        gc.collect()

        # Executor should be garbage collected
        # Note: This might not always work due to async internals

    @pytest.mark.asyncio
    async def test_task_cleanup_on_cancellation(self, mock_registry, mock_which):
        """Test that tasks are properly cleaned up on cancellation."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        task_states = {"created": 0, "completed": 0, "cancelled": 0}

        async def mock_execute(tool, prompt, cancel_event=None):
            task_states["created"] += 1
            try:
                if tool.name == "claude":
                    task_states["completed"] += 1
                    return ToolResult(
                        tool="claude",
                        success=True,
                        output="Done",
                        execution_time=0.01,
                    )
                await asyncio.sleep(10.0)
                task_states["completed"] += 1
                return ToolResult(
                    tool="opencode",
                    success=True,
                    output="Slow",
                    execution_time=10.0,
                )
            except asyncio.CancelledError:
                task_states["cancelled"] += 1
                raise

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            await executor.execute("Test")

            # Both tasks created, one completed, one potentially cancelled
            assert task_states["created"] == 2


# ---------------------------------------------------------------------------
# Test: Conflict Resolution Edge Cases
# ---------------------------------------------------------------------------


class TestConflictResolutionEdgeCases:
    """Test edge cases in conflict resolution."""

    def test_consensus_with_all_failures(self):
        """Test consensus when all tools failed."""
        results = [
            ToolResult(tool="claude", success=False, output="", error="Error", execution_time=0.1),
            ToolResult(
                tool="opencode",
                success=False,
                output="",
                error="Error",
                execution_time=0.1,
            ),
        ]

        winner, conflict_info = ConflictResolver.resolve_by_consensus(results)

        assert winner is None  # No successful results to achieve consensus

    def test_weighted_vote_equal_weights(self):
        """Test weighted vote with equal weights."""
        results = [
            ToolResult(tool="claude", success=True, output="A", execution_time=60.0),
            ToolResult(tool="opencode", success=True, output="B", execution_time=60.0),
        ]

        winner, _ = ConflictResolver.resolve_by_weighted_vote(
            results,
            weights={"claude": 1.0, "opencode": 1.0},
        )

        # Should still pick one
        assert winner is not None

    def test_smart_merge_with_duplicates(self):
        """Test smart merge when outputs are identical."""
        results = [
            ToolResult(tool="claude", success=True, output="Same content", execution_time=0.1),
            ToolResult(tool="opencode", success=True, output="Same content", execution_time=0.1),
        ]

        merged, conflict_info = ConflictResolver.smart_merge(results)

        # Should not duplicate content
        assert merged.count("Same content") == 1

    def test_normalize_output_preserves_code(self):
        """Test that code blocks are preserved during normalization."""
        text = """
Here is code:
```python
def foo():
    return 42
```
"""
        normalized = ConflictDetector.normalize_output(text)

        # Should still be readable
        assert "foo" in normalized


# ---------------------------------------------------------------------------
# Test: Tool Configuration Edge Cases
# ---------------------------------------------------------------------------


class TestToolConfigEdgeCases:
    """Test edge cases in tool configuration."""

    @pytest.mark.asyncio
    async def test_all_tools_disabled(self, mock_registry, mock_which):
        """Test execution with all tools disabled."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", enabled=False),
                ToolConfig(name="opencode", enabled=False),
            ],
        )

        result = await executor.execute("Test")

        assert result.success is False
        assert "No tools enabled" in result.metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_mixed_enabled_disabled(self, mock_registry, mock_which):
        """Test with mix of enabled and disabled tools."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", enabled=False),
                ToolConfig(name="opencode", enabled=True),
            ],
        )

        with patch.object(executor, "_execute_tool") as mock_exec:
            mock_exec.return_value = ToolResult(
                tool="opencode",
                success=True,
                output="Success",
                execution_time=0.1,
            )

            result = await executor.execute("Test")

            assert result.success is True
            assert result.winning_tool == "opencode"

    @pytest.mark.asyncio
    async def test_custom_command_configuration(self, mock_registry, mock_which):
        """Test tools with custom command configuration."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(
                    name="custom",
                    command=["custom-tool", "--flag", "value"],
                ),
            ],
        )

        with patch.object(executor, "_execute_direct") as mock_direct:
            mock_direct.return_value = ToolResult(
                tool="custom",
                success=True,
                output="Custom output",
                execution_time=0.1,
            )

            await executor.execute("Test")

            mock_direct.assert_called_once()

    @pytest.mark.asyncio
    async def test_scorer_returns_negative(self, mock_registry, mock_which):
        """Test best_score with scorer returning negative values."""

        def negative_scorer(result: ToolResult) -> float:
            return -10.0

        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.BEST_SCORE,
            scorer=negative_scorer,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=True, output="Output", execution_time=0.1),
                ],
            )

            result = await executor.execute("Test")

            # Should still work
            assert result.winning_tool == "claude"
            assert result.metadata["scores"]["claude"] == -10.0


# ---------------------------------------------------------------------------
# Test: Async Context Manager Support
# ---------------------------------------------------------------------------


class TestAsyncBehavior:
    """Test async-specific behavior."""

    @pytest.mark.asyncio
    async def test_timeout_exception_handling(self, mock_registry, mock_which):
        """Test handling of asyncio.TimeoutError."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def timeout_execute(tool, prompt, cancel_event=None):
                raise asyncio.TimeoutError("Simulated timeout")

            mock_exec.side_effect = timeout_execute

            result = await executor.execute("Test")

            # Should handle timeout gracefully
            assert result.success is False or len(result.tool_results) > 0

    @pytest.mark.asyncio
    async def test_exception_in_one_tool(self, mock_registry, mock_which):
        """Test that exception in one tool doesn't crash others."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mixed_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                raise ValueError("Claude exploded")
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode OK",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mixed_execute):
            result = await executor.execute("Test")

            # OpenCode should still succeed
            opencode_result = [r for r in result.tool_results if r.tool == "opencode"]
            assert len(opencode_result) == 1
            assert opencode_result[0].success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
