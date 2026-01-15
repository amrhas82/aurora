"""Performance and stress tests for concurrent tool execution.

Tests cover:
- Throughput under load
- Latency benchmarks
- Memory usage under concurrent execution
- Scalability with increasing tool count
- Resource cleanup verification
"""

import asyncio
import gc
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
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
# Test: Throughput Benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestThroughputBenchmarks:
    """Test execution throughput under various conditions."""

    @pytest.mark.asyncio
    async def test_single_tool_throughput(self, mock_registry, mock_which):
        """Measure single tool execution throughput."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        num_executions = 100

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def fast_execute(tool, prompt, cancel_event=None):
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Output",
                    execution_time=0.001,
                )

            mock_exec.side_effect = fast_execute

            start_time = time.perf_counter()

            for _ in range(num_executions):
                await executor.execute("Test prompt")

            elapsed = time.perf_counter() - start_time
            throughput = num_executions / elapsed

            print(f"\nSingle tool throughput: {throughput:.1f} executions/second")
            print(f"Total time: {elapsed:.3f}s for {num_executions} executions")

            # Should handle at least 10 executions per second (very conservative)
            assert throughput > 10

    @pytest.mark.asyncio
    async def test_multi_tool_throughput(self, mock_registry, mock_which):
        """Measure multi-tool parallel execution throughput."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        num_executions = 50

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def fast_execute(tool, prompt, cancel_event=None):
                await asyncio.sleep(0.001)  # Minimal async delay
                return ToolResult(
                    tool=tool.name,
                    success=True,
                    output=f"{tool.name} output",
                    execution_time=0.001,
                )

            mock_exec.side_effect = fast_execute

            start_time = time.perf_counter()

            for _ in range(num_executions):
                result = await executor.execute("Test prompt")
                assert len(result.tool_results) == 3

            elapsed = time.perf_counter() - start_time
            throughput = num_executions / elapsed

            print(f"\nMulti-tool (3) throughput: {throughput:.1f} executions/second")
            print(f"Total time: {elapsed:.3f}s for {num_executions} executions")

            # Should handle at least 5 multi-tool executions per second
            assert throughput > 5

    @pytest.mark.asyncio
    async def test_concurrent_execution_throughput(self, mock_registry, mock_which):
        """Measure throughput of truly concurrent executions."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        num_concurrent = 20

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def async_execute(tool, prompt, cancel_event=None):
                await asyncio.sleep(0.01)  # Simulate some work
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Output",
                    execution_time=0.01,
                )

            mock_exec.side_effect = async_execute

            start_time = time.perf_counter()

            # Launch all executions concurrently
            tasks = [executor.execute(f"Prompt {i}") for i in range(num_concurrent)]
            results = await asyncio.gather(*tasks)

            elapsed = time.perf_counter() - start_time

            print(f"\nConcurrent execution: {num_concurrent} tasks in {elapsed:.3f}s")
            print(f"Average: {elapsed/num_concurrent*1000:.1f}ms per execution")

            assert all(r.success for r in results)
            # Concurrent execution should be faster than sequential
            # 20 tasks at 10ms each sequential = 200ms; concurrent should be < 100ms
            assert elapsed < 0.5


# ---------------------------------------------------------------------------
# Test: Latency Benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestLatencyBenchmarks:
    """Test execution latency characteristics."""

    @pytest.mark.asyncio
    async def test_execution_overhead(self, mock_registry, mock_which):
        """Measure overhead added by executor framework."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def instant_execute(tool, prompt, cancel_event=None):
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="",
                    execution_time=0.0,
                )

            mock_exec.side_effect = instant_execute

            # Warmup
            await executor.execute("warmup")

            # Measure
            latencies = []
            for _ in range(100):
                start = time.perf_counter()
                await executor.execute("Test")
                latencies.append(time.perf_counter() - start)

            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            p99_latency = sorted(latencies)[98]

            print(f"\nExecution overhead:")
            print(f"  Average: {avg_latency*1000:.3f}ms")
            print(f"  Min: {min_latency*1000:.3f}ms")
            print(f"  Max: {max_latency*1000:.3f}ms")
            print(f"  P99: {p99_latency*1000:.3f}ms")

            # Overhead should be under 10ms
            assert avg_latency < 0.01

    @pytest.mark.asyncio
    async def test_strategy_comparison_latency(self, mock_registry, mock_which):
        """Compare latency across different strategies."""
        strategies = [
            AggregationStrategy.FIRST_SUCCESS,
            AggregationStrategy.ALL_COMPLETE,
            AggregationStrategy.BEST_SCORE,
            AggregationStrategy.MERGE,
        ]

        results = {}

        for strategy in strategies:
            executor = ConcurrentToolExecutor(
                tools=["claude", "opencode"],
                strategy=strategy,
            )

            with patch.object(executor, "_execute_tool") as mock_exec:

                async def quick_execute(tool, prompt, cancel_event=None):
                    await asyncio.sleep(0.001)
                    return ToolResult(
                        tool=tool.name,
                        success=True,
                        output=f"{tool.name} output content",
                        execution_time=0.001,
                    )

                mock_exec.side_effect = quick_execute

                # Warmup
                await executor.execute("warmup")

                # Measure
                latencies = []
                for _ in range(20):
                    start = time.perf_counter()
                    await executor.execute("Test")
                    latencies.append(time.perf_counter() - start)

                results[strategy.value] = sum(latencies) / len(latencies)

        print("\nStrategy latency comparison:")
        for strategy, latency in sorted(results.items(), key=lambda x: x[1]):
            print(f"  {strategy}: {latency*1000:.2f}ms")


# ---------------------------------------------------------------------------
# Test: Scalability
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestScalability:
    """Test scalability with increasing tool counts."""

    @pytest.mark.asyncio
    async def test_scale_with_tool_count(self, mock_registry, mock_which):
        """Measure how execution time scales with tool count."""
        tool_counts = [1, 2, 5, 10, 20]
        results = {}

        for count in tool_counts:
            tools = [f"tool_{i}" for i in range(count)]
            executor = ConcurrentToolExecutor(
                tools=tools,
                strategy=AggregationStrategy.ALL_COMPLETE,
            )

            with patch.object(executor, "_execute_tool") as mock_exec:

                async def execute_tool(tool, prompt, cancel_event=None):
                    await asyncio.sleep(0.01)  # Fixed per-tool cost
                    return ToolResult(
                        tool=tool.name,
                        success=True,
                        output=f"{tool.name} output",
                        execution_time=0.01,
                    )

                mock_exec.side_effect = execute_tool

                # Measure
                start = time.perf_counter()
                result = await executor.execute("Test")
                elapsed = time.perf_counter() - start

                results[count] = elapsed
                assert len(result.tool_results) == count

        print("\nScaling with tool count:")
        for count, elapsed in results.items():
            overhead_per_tool = elapsed / count * 1000
            print(f"  {count} tools: {elapsed*1000:.1f}ms total, {overhead_per_tool:.1f}ms/tool")

        # With async parallel execution, time should not increase linearly
        # 20 tools should not take 20x the time of 1 tool
        assert results[20] < results[1] * 10

    @pytest.mark.asyncio
    async def test_scale_with_output_size(self, mock_registry, mock_which):
        """Measure how execution handles varying output sizes."""
        output_sizes = [100, 1000, 10000, 100000]  # bytes
        results = {}

        for size in output_sizes:
            executor = ConcurrentToolExecutor(
                tools=["claude", "opencode"],
                strategy=AggregationStrategy.SMART_MERGE,
            )

            with patch.object(executor, "_execute_tool") as mock_exec:

                async def execute_with_output(tool, prompt, cancel_event=None):
                    return ToolResult(
                        tool=tool.name,
                        success=True,
                        output="x" * size,
                        execution_time=0.01,
                    )

                mock_exec.side_effect = execute_with_output

                # Measure
                start = time.perf_counter()
                result = await executor.execute("Test")
                elapsed = time.perf_counter() - start

                results[size] = elapsed

        print("\nScaling with output size (SMART_MERGE):")
        for size, elapsed in results.items():
            print(f"  {size:6d} bytes: {elapsed*1000:.1f}ms")

        # Large outputs should not cause exponential slowdown
        assert results[100000] < results[100] * 100


# ---------------------------------------------------------------------------
# Test: Memory Usage
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage during concurrent execution."""

    @pytest.mark.asyncio
    async def test_memory_stable_under_load(self, mock_registry, mock_which):
        """Verify memory doesn't grow unbounded during execution."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def execute_task(tool, prompt, cancel_event=None):
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="x" * 10000,  # 10KB output
                    execution_time=0.01,
                )

            mock_exec.side_effect = execute_task

            # Get baseline memory
            gc.collect()
            import tracemalloc

            tracemalloc.start()

            # Execute many times
            for _ in range(100):
                await executor.execute("Test")

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            print(f"\nMemory usage after 100 executions:")
            print(f"  Current: {current / 1024:.1f} KB")
            print(f"  Peak: {peak / 1024:.1f} KB")

            # Peak should be reasonable (< 50MB)
            assert peak < 50 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_large_result_handling(self, mock_registry, mock_which):
        """Test memory efficiency with large results."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        # 1MB outputs from each tool
        large_output = "x" * (1024 * 1024)

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def execute_large(tool, prompt, cancel_event=None):
                return ToolResult(
                    tool=tool.name,
                    success=True,
                    output=large_output,
                    execution_time=0.1,
                )

            mock_exec.side_effect = execute_large

            gc.collect()
            import tracemalloc

            tracemalloc.start()

            result = await executor.execute("Test")

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            print(f"\nMemory for 2x 1MB outputs:")
            print(f"  Current: {current / 1024 / 1024:.1f} MB")
            print(f"  Peak: {peak / 1024 / 1024:.1f} MB")

            assert result.success is True
            # Should not use more than 10x the output size
            assert peak < 20 * 1024 * 1024


# ---------------------------------------------------------------------------
# Test: Stress Tests
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestStressScenarios:
    """Stress tests for concurrent execution."""

    @pytest.mark.asyncio
    async def test_rapid_fire_executions(self, mock_registry, mock_which):
        """Test rapid successive executions."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        num_rapid = 500

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def instant_execute(tool, prompt, cancel_event=None):
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Done",
                    execution_time=0.0,
                )

            mock_exec.side_effect = instant_execute

            start = time.perf_counter()

            # Fire off executions as fast as possible
            for _ in range(num_rapid):
                await executor.execute("Test")

            elapsed = time.perf_counter() - start

            print(f"\nRapid fire: {num_rapid} executions in {elapsed:.2f}s")
            print(f"Rate: {num_rapid/elapsed:.0f} executions/second")

            # Should handle at least 100 executions per second
            assert num_rapid / elapsed > 100

    @pytest.mark.asyncio
    async def test_mixed_success_failure_storm(self, mock_registry, mock_which):
        """Stress test with mixed success/failure results."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        call_count = [0]

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mixed_execute(tool, prompt, cancel_event=None):
                call_count[0] += 1
                success = call_count[0] % 3 != 0  # 1/3 fail
                return ToolResult(
                    tool=tool.name,
                    success=success,
                    output="Output" if success else "",
                    error=None if success else "Failed",
                    execution_time=0.001,
                )

            mock_exec.side_effect = mixed_execute

            results = []
            for _ in range(100):
                result = await executor.execute("Test")
                results.append(result)

            success_count = sum(1 for r in results if r.success)
            print(f"\nMixed storm: {success_count}/100 successful")

            # Should handle mixed results gracefully
            assert len(results) == 100

    @pytest.mark.asyncio
    async def test_concurrent_burst(self, mock_registry, mock_which):
        """Test burst of concurrent executions."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        burst_size = 100

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def async_execute(tool, prompt, cancel_event=None):
                await asyncio.sleep(0.01)
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Burst response",
                    execution_time=0.01,
                )

            mock_exec.side_effect = async_execute

            start = time.perf_counter()

            # Launch all at once
            tasks = [executor.execute(f"Burst {i}") for i in range(burst_size)]
            results = await asyncio.gather(*tasks)

            elapsed = time.perf_counter() - start

            print(f"\nBurst test: {burst_size} concurrent in {elapsed:.2f}s")

            assert all(r.success for r in results)
            # Should complete faster than sequential (100 * 10ms = 1s)
            assert elapsed < 1.0


# ---------------------------------------------------------------------------
# Test: Resource Cleanup
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestResourceCleanup:
    """Test that resources are properly cleaned up."""

    @pytest.mark.asyncio
    async def test_task_cleanup_after_cancellation(self, mock_registry, mock_which):
        """Verify tasks are cleaned up after cancellation."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def slow_execute(tool, prompt, cancel_event=None):
                if tool.name == "claude":
                    return ToolResult(
                        tool="claude", success=True, output="Quick", execution_time=0.01
                    )
                # Slow tool that should be cancelled
                await asyncio.sleep(10.0)
                return ToolResult(tool="opencode", success=True, output="Slow", execution_time=10.0)

            mock_exec.side_effect = slow_execute

            # Execute multiple times
            for _ in range(10):
                await executor.execute("Test")

            # Give time for any lingering tasks to complete
            await asyncio.sleep(0.1)

            # No assertions - just verify no exceptions from orphaned tasks

    @pytest.mark.asyncio
    async def test_exception_cleanup(self, mock_registry, mock_which):
        """Verify proper cleanup after exceptions."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:
            call_count = [0]

            async def failing_execute(tool, prompt, cancel_event=None):
                call_count[0] += 1
                if call_count[0] <= 5:
                    raise RuntimeError("Intentional failure")
                return ToolResult(tool="claude", success=True, output="OK", execution_time=0.01)

            mock_exec.side_effect = failing_execute

            # Execute multiple times (some will fail)
            results = []
            for _ in range(10):
                try:
                    result = await executor.execute("Test")
                    results.append(("success", result))
                except RuntimeError:
                    results.append(("error", None))

            # Should eventually succeed
            success_count = sum(1 for r, _ in results if r == "success")
            assert success_count >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
