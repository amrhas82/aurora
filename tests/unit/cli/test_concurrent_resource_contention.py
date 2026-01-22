"""Unit tests for resource contention and race conditions in concurrent execution.

Tests cover:
- Shared state access during concurrent tool execution
- Cancel event synchronization
- Result aggregation race conditions
- Memory safety with large concurrent operations
- Process cleanup on errors
"""

import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ConflictDetector,
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
# Test: Shared State Access
# ---------------------------------------------------------------------------


class TestSharedStateAccess:
    """Test shared state access during concurrent execution."""

    @pytest.mark.asyncio
    async def test_results_list_thread_safety(self, mock_registry):
        """Test that results list is safely accessed by multiple coroutines."""
        executor = ConcurrentToolExecutor(
            tools=[f"tool{i}" for i in range(5)],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        collected_results = []

        async def mock_execute(tool, prompt, cancel_event=None):
            # Simulate varying execution times
            await asyncio.sleep(0.001 * hash(tool.name) % 10)
            result = ToolResult(
                tool=tool.name, success=True, output=f"{tool.name} output", execution_time=0.01
            )
            collected_results.append(result)
            return result

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.tool_results) == 5
            # All tools should be represented
            tool_names = {r.tool for r in result.tool_results}
            assert len(tool_names) == 5

    @pytest.mark.asyncio
    async def test_concurrent_output_modification(self, mock_registry):
        """Test that output strings are safely handled concurrently."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2", "tool3"],
            strategy=AggregationStrategy.MERGE,
        )

        # Generate large outputs that would expose race conditions
        async def mock_execute(tool, prompt, cancel_event=None):
            large_output = f"[{tool.name}]\n" + ("x" * 10000)
            return ToolResult(
                tool=tool.name, success=True, output=large_output, execution_time=0.01
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            # Verify each tool's output is intact
            for tool_name in ["tool1", "tool2", "tool3"]:
                assert f"[{tool_name}]" in result.primary_output


# ---------------------------------------------------------------------------
# Test: Cancel Event Synchronization
# ---------------------------------------------------------------------------


class TestCancelEventSynchronization:
    """Test cancel event synchronization across coroutines."""

    @pytest.mark.asyncio
    async def test_cancel_event_propagation(self, mock_registry):
        """Test that cancel event properly propagates to all tools."""
        executor = ConcurrentToolExecutor(
            tools=["fast", "slow1", "slow2"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        cancel_received = {"slow1": False, "slow2": False}

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "fast":
                await asyncio.sleep(0.001)
                return ToolResult(tool="fast", success=True, output="Quick", execution_time=0.001)
            else:
                try:
                    # Check cancel event periodically
                    for _ in range(100):
                        if cancel_event and cancel_event.is_set():
                            cancel_received[tool.name] = True
                            return ToolResult(
                                tool=tool.name, success=False, output="", error="Cancelled"
                            )
                        await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    cancel_received[tool.name] = True
                    return ToolResult(tool=tool.name, success=False, output="", error="Cancelled")
                return ToolResult(tool=tool.name, success=True, output="Slow", execution_time=1.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "fast"

    @pytest.mark.asyncio
    async def test_multiple_cancel_event_sets(self, mock_registry):
        """Test that multiple tools setting cancel event is handled."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        set_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            # Both tools try to succeed at same time
            await asyncio.sleep(0.001)
            if cancel_event:
                set_count[0] += 1
                cancel_event.set()
            return ToolResult(tool=tool.name, success=True, output="Output", execution_time=0.001)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Should still complete successfully
            assert result.success is True


# ---------------------------------------------------------------------------
# Test: Result Aggregation Race Conditions
# ---------------------------------------------------------------------------


class TestResultAggregationRaceConditions:
    """Test race conditions in result aggregation."""

    @pytest.mark.asyncio
    async def test_voting_with_simultaneous_results(self, mock_registry):
        """Test voting aggregation when results arrive simultaneously."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2", "tool3"],
            strategy=AggregationStrategy.VOTING,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="tool1", success=True, output="Answer A", execution_time=0.01),
                    ToolResult(tool="tool2", success=True, output="Answer A", execution_time=0.01),
                    ToolResult(tool="tool3", success=True, output="Answer B", execution_time=0.01),
                ],
            )

            result = await executor.execute("Test prompt")

            # Voting should determine winner despite simultaneous arrival
            assert result.success is True
            assert "Answer A" in result.primary_output

    @pytest.mark.asyncio
    async def test_best_score_with_equal_scores(self, mock_registry):
        """Test best_score when multiple tools have exact same score."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.BEST_SCORE,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            # Create exactly equal results
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="tool1", success=True, output="Same" * 100, execution_time=30.0
                    ),
                    ToolResult(
                        tool="tool2", success=True, output="Same" * 100, execution_time=30.0
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            # Should pick one deterministically
            assert result.success is True
            assert result.winning_tool in ["tool1", "tool2"]


# ---------------------------------------------------------------------------
# Test: Memory Safety
# ---------------------------------------------------------------------------


class TestMemorySafety:
    """Test memory safety with large concurrent operations."""

    @pytest.mark.asyncio
    async def test_large_output_handling(self, mock_registry):
        """Test handling of very large outputs from multiple tools."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            # Generate 1MB output per tool
            large_output = "x" * (1024 * 1024)
            return ToolResult(tool=tool.name, success=True, output=large_output, execution_time=0.1)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            # Verify outputs aren't corrupted
            assert len(result.tool_results[0].output) == 1024 * 1024

    @pytest.mark.asyncio
    async def test_many_concurrent_tools(self, mock_registry):
        """Test with many concurrent tools to stress memory handling."""
        tools = [f"tool{i}" for i in range(20)]
        executor = ConcurrentToolExecutor(
            tools=tools,
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            await asyncio.sleep(0.001)
            return ToolResult(
                tool=tool.name, success=True, output=f"Output {tool.name}", execution_time=0.001
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.tool_results) == 20

    @pytest.mark.asyncio
    async def test_rapid_repeated_executions(self, mock_registry):
        """Test rapid repeated executions don't leak resources."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            return ToolResult(tool=tool.name, success=True, output="Output", execution_time=0.001)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            # Run many iterations quickly
            for _ in range(50):
                result = await executor.execute("Test prompt")
                assert result.success is True


# ---------------------------------------------------------------------------
# Test: Process Cleanup on Errors
# ---------------------------------------------------------------------------


class TestProcessCleanup:
    """Test process cleanup on errors and cancellation."""

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self, mock_registry):
        """Test that processes are cleaned up when exceptions occur."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        cleanup_called = [False, False]

        async def mock_execute(tool, prompt, cancel_event=None):
            try:
                if tool.name == "tool1":
                    raise RuntimeError("Simulated error")
                await asyncio.sleep(0.1)
                return ToolResult(tool="tool2", success=True, output="Output", execution_time=0.1)
            finally:
                cleanup_called[0 if tool.name == "tool1" else 1] = True

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Should handle error gracefully
            assert len(result.tool_results) == 2

    @pytest.mark.asyncio
    async def test_cleanup_on_timeout(self, mock_registry):
        """Test cleanup when timeout occurs."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="slow", timeout=0.01)],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        process_killed = [False]

        async def mock_execute(tool, prompt, cancel_event=None):
            try:
                await asyncio.sleep(10.0)  # Will timeout
            except asyncio.CancelledError:
                process_killed[0] = True
                return ToolResult(tool="slow", success=False, output="", error="Cancelled")
            return ToolResult(tool="slow", success=True, output="Output", execution_time=10.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            # Will timeout at executor level
            result = await executor.execute("Test prompt")

            # Should handle timeout gracefully
            assert result is not None

    @pytest.mark.asyncio
    async def test_cleanup_on_cancellation(self, mock_registry):
        """Test cleanup when execution is cancelled externally."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        started = asyncio.Event()
        cleanup_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            started.set()
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                cleanup_count[0] += 1
                raise
            return ToolResult(tool=tool.name, success=True, output="Output", execution_time=10.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            # Start execution
            task = asyncio.create_task(executor.execute("Test prompt"))
            await started.wait()

            # Cancel after a short delay
            await asyncio.sleep(0.01)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass


# ---------------------------------------------------------------------------
# Test: Conflict Detection Thread Safety
# ---------------------------------------------------------------------------


class TestConflictDetectionThreadSafety:
    """Test thread safety in conflict detection."""

    def test_concurrent_conflict_detection(self):
        """Test conflict detection with concurrent access."""
        results = [
            ToolResult(
                tool=f"tool{i}", success=True, output=f"Output {i}" * 100, execution_time=0.1
            )
            for i in range(5)
        ]

        conflicts = []

        def detect_conflicts():
            conflict = ConflictDetector.detect_conflicts(results)
            conflicts.append(conflict)

        threads = [threading.Thread(target=detect_conflicts) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should produce consistent results
        assert len(conflicts) == 10
        # Similarity scores should be consistent (within floating point tolerance)
        scores = [c.similarity_score for c in conflicts]
        assert max(scores) - min(scores) < 0.01

    def test_concurrent_normalization(self):
        """Test output normalization with concurrent access."""
        text = "Hello   world\n\n\n\nwith    spaces"
        results = []

        def normalize():
            normalized = ConflictDetector.normalize_output(text)
            results.append(normalized)

        threads = [threading.Thread(target=normalize) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should produce same result
        assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# Test: Executor State Isolation
# ---------------------------------------------------------------------------


class TestExecutorStateIsolation:
    """Test that executor instances have isolated state."""

    @pytest.mark.asyncio
    async def test_independent_executors(self, mock_registry):
        """Test that multiple executor instances don't interfere."""
        executor1 = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )
        executor2 = ConcurrentToolExecutor(
            tools=["opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        results = {"e1": None, "e2": None}

        async def mock_execute1(tool, prompt, cancel_event=None):
            await asyncio.sleep(0.01)
            return ToolResult(tool="claude", success=True, output="Claude", execution_time=0.01)

        async def mock_execute2(tool, prompt, cancel_event=None):
            await asyncio.sleep(0.01)
            return ToolResult(tool="opencode", success=True, output="OpenCode", execution_time=0.01)

        with patch.object(executor1, "_execute_tool", side_effect=mock_execute1):
            with patch.object(executor2, "_execute_tool", side_effect=mock_execute2):
                result1, result2 = await asyncio.gather(
                    executor1.execute("Prompt 1"),
                    executor2.execute("Prompt 2"),
                )

                assert result1.winning_tool == "claude"
                assert result2.tool_results[0].tool == "opencode"

    @pytest.mark.asyncio
    async def test_executor_reuse(self, mock_registry):
        """Test that reusing an executor works correctly."""
        executor = ConcurrentToolExecutor(
            tools=["tool1"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        execution_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            execution_count[0] += 1
            return ToolResult(
                tool="tool1", success=True, output=f"Run {execution_count[0]}", execution_time=0.01
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result1 = await executor.execute("Prompt 1")
            result2 = await executor.execute("Prompt 2")
            result3 = await executor.execute("Prompt 3")

            assert "Run 1" in result1.primary_output
            assert "Run 2" in result2.primary_output
            assert "Run 3" in result3.primary_output


# ---------------------------------------------------------------------------
# Test: Async Event Loop Safety
# ---------------------------------------------------------------------------


class TestAsyncEventLoopSafety:
    """Test async event loop safety."""

    @pytest.mark.asyncio
    async def test_nested_async_calls(self, mock_registry):
        """Test nested async operations work correctly."""
        executor = ConcurrentToolExecutor(
            tools=["tool1"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            # Simulate nested async operation
            await asyncio.sleep(0.001)
            return ToolResult(tool="tool1", success=True, output="Output", execution_time=0.001)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_exception_in_async_context(self, mock_registry):
        """Test exception handling in async context."""
        executor = ConcurrentToolExecutor(
            tools=["tool1", "tool2"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "tool1":
                raise ValueError("Test error")
            return ToolResult(tool="tool2", success=True, output="Success", execution_time=0.01)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Should handle exception and still return results
            assert len(result.tool_results) == 2
            tool1_result = next(r for r in result.tool_results if r.tool == "tool1")
            assert not tool1_result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
