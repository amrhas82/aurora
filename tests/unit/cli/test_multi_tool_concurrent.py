"""Unit tests for multi-tool concurrent execution scenarios.

Tests cover advanced concurrent execution patterns when running
multiple AI tools (Claude, OpenCode) simultaneously:

- Race conditions and timing-sensitive behavior
- Tool failure recovery and partial success handling
- Conflict detection between tool outputs
- Strategy-specific edge cases
- Resource management under concurrent load
- Mixed tool provider and direct execution paths
"""

import asyncio
from dataclasses import dataclass
from typing import Any
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


@pytest.fixture
def claude_opencode_executor(mock_registry, mock_which):
    """Create executor with Claude and OpenCode."""
    return ConcurrentToolExecutor(
        tools=["claude", "opencode"],
        strategy=AggregationStrategy.FIRST_SUCCESS,
    )


# ---------------------------------------------------------------------------
# Test: Race Conditions and Timing
# ---------------------------------------------------------------------------


class TestRaceConditions:
    """Test race conditions in concurrent execution."""

    @pytest.mark.asyncio
    async def test_near_simultaneous_completion(self, mock_registry, mock_which):
        """Test when tools complete at nearly the same time."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        completion_order = []

        async def mock_execute(tool, prompt, cancel_event=None):
            # Both complete nearly simultaneously
            await asyncio.sleep(0.001)
            completion_order.append(tool.name)
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} output",
                execution_time=0.001,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            # One should win (order may vary)
            assert result.winning_tool in ["claude", "opencode"]
            assert len(completion_order) >= 1

    @pytest.mark.asyncio
    async def test_interleaved_success_failure(self, mock_registry, mock_which):
        """Test alternating success/failure between tools."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        call_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            call_count[0] += 1
            success = call_count[0] % 2 == 0  # Alternate success/failure
            return ToolResult(
                tool=tool.name,
                success=success,
                output=f"{tool.name} {'success' if success else 'failed'}",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # At least one should succeed
            successful = [r for r in result.tool_results if r.success]
            assert len(successful) >= 1

    @pytest.mark.asyncio
    async def test_first_success_cancellation_race(self, mock_registry, mock_which):
        """Test cancellation propagation in first_success strategy."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        cancellation_received = {"opencode": False}

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Quick response",
                    execution_time=0.01,
                )
            else:
                # Slow tool that checks for cancellation
                try:
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    cancellation_received["opencode"] = True
                    raise
                return ToolResult(
                    tool="opencode",
                    success=True,
                    output="Slow response",
                    execution_time=0.5,
                )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "claude"


# ---------------------------------------------------------------------------
# Test: Tool Failure Recovery
# ---------------------------------------------------------------------------


class TestToolFailureRecovery:
    """Test handling of tool failures in concurrent execution."""

    @pytest.mark.asyncio
    async def test_graceful_degradation_single_failure(self, mock_registry, mock_which):
        """Test that single tool failure doesn't break entire execution."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                raise RuntimeError("Claude crashed unexpectedly")
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode working",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Should succeed with one tool working
            assert result.success is True
            assert result.winning_tool == "opencode"
            # Claude should have error recorded
            claude_result = [r for r in result.tool_results if r.tool == "claude"][0]
            assert claude_result.success is False

    @pytest.mark.asyncio
    async def test_all_tools_timeout(self, mock_registry, mock_which):
        """Test behavior when all tools timeout."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", timeout=0.01),
                ToolConfig(name="opencode", timeout=0.01),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            await asyncio.sleep(1.0)  # Much longer than timeout
            return ToolResult(
                tool=tool.name,
                success=True,
                output="Should not reach",
                execution_time=1.0,
            )

        with patch.object(executor, "_execute_tool") as mock:
            # Simulate timeout result
            mock.return_value = ToolResult(
                tool="claude",
                success=False,
                output="",
                error="Timeout after 0.01s",
                exit_code=-1,
                execution_time=0.01,
            )

            result = await executor.execute("Test prompt")

            assert result.success is False

    @pytest.mark.asyncio
    async def test_mixed_timeout_and_failure(self, mock_registry, mock_which):
        """Test handling mixed timeout and regular failures."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(
                    tool="claude",
                    success=False,
                    output="",
                    error="Timeout after 60s",
                    exit_code=-1,
                    execution_time=60.0,
                )
            elif tool.name == "opencode":
                return ToolResult(
                    tool="opencode",
                    success=False,
                    output="",
                    error="Connection refused",
                    exit_code=1,
                    execution_time=0.1,
                )
            else:
                return ToolResult(
                    tool="cursor",
                    success=True,
                    output="Cursor works!",
                    execution_time=0.5,
                )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "cursor"
            # Verify all failures recorded
            failures = [r for r in result.tool_results if not r.success]
            assert len(failures) == 2


# ---------------------------------------------------------------------------
# Test: Conflict Detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    """Test ConflictDetector functionality."""

    def test_identical_outputs_no_conflict(self):
        """Test that identical outputs show no conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42", execution_time=1.0),
            ToolResult(
                tool="opencode", success=True, output="The answer is 42", execution_time=1.0
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        assert conflict_info.severity == ConflictSeverity.NONE
        assert conflict_info.similarity_score >= 0.95

    def test_minor_formatting_differences(self):
        """Test that whitespace differences are detected as formatting."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42", execution_time=1.0),
            ToolResult(
                tool="opencode", success=True, output="The  answer   is  42", execution_time=1.0
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        # After normalization these should be nearly identical
        assert conflict_info.severity in (ConflictSeverity.NONE, ConflictSeverity.FORMATTING)

    def test_major_conflict_detection(self):
        """Test detection of major conflicts."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="You should use Python for this task. Python is great for scripting.",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="I recommend using Rust instead. Rust provides memory safety.",
                execution_time=1.0,
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        assert conflict_info.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)
        assert conflict_info.similarity_score < 0.85

    def test_single_result_no_conflict(self):
        """Test that single result cannot have conflicts."""
        results = [
            ToolResult(tool="claude", success=True, output="Only one output", execution_time=1.0),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        assert conflict_info.severity == ConflictSeverity.NONE
        assert "Insufficient" in conflict_info.description

    def test_conflict_with_code_blocks(self):
        """Test conflict detection for code block differences."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="Here is the implementation:\n```python\ndef calculate_sum(a, b):\n    return a + b\n```\nThis adds two numbers together using simple addition.",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="The solution uses subtraction:\n```python\ndef calculate_diff(x, y):\n    return x - y\n```\nThis subtracts the second number from the first.",
                execution_time=1.0,
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        # Significantly different code should be detected as conflict
        assert conflict_info.severity in (
            ConflictSeverity.MINOR,
            ConflictSeverity.MODERATE,
            ConflictSeverity.MAJOR,
        )

    def test_normalize_output(self):
        """Test output normalization."""
        text = "  Hello   World  \n\n\n\n  Test  "
        normalized = ConflictDetector.normalize_output(text)

        assert "  " not in normalized  # No double spaces
        assert "\n\n\n" not in normalized  # No triple newlines

    def test_extract_code_blocks(self):
        """Test code block extraction."""
        text = """
        Here is some code:
        ```python
        def hello():
            print("hi")
        ```
        And more:
        ```javascript
        console.log("hi");
        ```
        """

        blocks = ConflictDetector.extract_code_blocks(text)

        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[1][0] == "javascript"


# ---------------------------------------------------------------------------
# Test: Conflict Resolution
# ---------------------------------------------------------------------------


class TestConflictResolution:
    """Test ConflictResolver functionality."""

    def test_resolve_by_consensus_success(self):
        """Test consensus resolution with high agreement."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42", execution_time=1.0),
            ToolResult(
                tool="opencode", success=True, output="The answer is 42", execution_time=1.0
            ),
        ]

        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.80)

        assert winner is not None
        assert winner.output == "The answer is 42"
        assert conflict_info.similarity_score >= 0.80

    def test_resolve_by_consensus_failure(self):
        """Test consensus resolution when no agreement."""
        results = [
            ToolResult(
                tool="claude", success=True, output="Use Python for this.", execution_time=1.0
            ),
            ToolResult(
                tool="opencode", success=True, output="Use Rust for this.", execution_time=1.0
            ),
        ]

        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.90)

        assert winner is None  # No consensus
        assert conflict_info.similarity_score < 0.90

    def test_resolve_by_weighted_vote(self):
        """Test weighted voting resolution."""
        results = [
            ToolResult(
                tool="claude", success=True, output="Answer A" * 100, execution_time=10.0
            ),  # Slow, long
            ToolResult(
                tool="opencode", success=True, output="Answer B", execution_time=1.0
            ),  # Fast, short
        ]

        # Weight claude higher
        winner, conflict_info = ConflictResolver.resolve_by_weighted_vote(
            results, weights={"claude": 5.0, "opencode": 1.0}
        )

        assert winner is not None
        assert winner.tool == "claude"

    def test_smart_merge_similar_outputs(self):
        """Test smart merge with similar outputs."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42.", execution_time=1.0),
            ToolResult(
                tool="opencode", success=True, output="The answer is 42", execution_time=1.0
            ),
        ]

        merged, conflict_info = ConflictResolver.smart_merge(results)

        # Should return longest when outputs are similar
        assert "42" in merged
        assert conflict_info.severity in (ConflictSeverity.NONE, ConflictSeverity.FORMATTING)

    def test_smart_merge_different_outputs(self):
        """Test smart merge with different outputs."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="First unique paragraph.\n\nSecond unique paragraph.",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="Completely different content.\n\nMore different stuff.",
                execution_time=1.0,
            ),
        ]

        merged, conflict_info = ConflictResolver.smart_merge(results)

        # Should include content from both when different
        assert "Merged Output" in merged or len(merged) > len(results[0].output)


# ---------------------------------------------------------------------------
# Test: Strategy Edge Cases
# ---------------------------------------------------------------------------


class TestStrategyEdgeCases:
    """Test edge cases for aggregation strategies."""

    @pytest.mark.asyncio
    async def test_voting_tie_breaker(self, mock_registry, mock_which):
        """Test voting strategy when there's a tie."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor", "copilot"],
            strategy=AggregationStrategy.VOTING,
        )

        # All different outputs - no majority
        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=True, output="Answer A", execution_time=0.1),
                    ToolResult(
                        tool="opencode", success=True, output="Answer B", execution_time=0.1
                    ),
                    ToolResult(tool="cursor", success=True, output="Answer C", execution_time=0.1),
                    ToolResult(tool="copilot", success=True, output="Answer D", execution_time=0.1),
                ],
            )

            result = await executor.execute("Test prompt")

            # Should still return a result (first by group size)
            assert result.success is True
            assert result.winning_tool is not None

    @pytest.mark.asyncio
    async def test_best_score_all_zero(self, mock_registry, mock_which):
        """Test best_score when all results have zero score."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.BEST_SCORE,
            scorer=lambda r: 0.0,  # All get zero score
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=False, output="Error", execution_time=0.1),
                    ToolResult(tool="opencode", success=False, output="Error", execution_time=0.1),
                ],
            )

            result = await executor.execute("Test prompt")

            # Should return first result
            assert result.winning_tool is not None

    @pytest.mark.asyncio
    async def test_merge_with_empty_outputs(self, mock_registry, mock_which):
        """Test merge strategy with empty outputs."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.MERGE,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=True, output="", execution_time=0.1),
                    ToolResult(
                        tool="opencode", success=True, output="Only content", execution_time=0.1
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            # Should handle empty output gracefully
            assert result.success is True
            assert "=== opencode ===" in result.primary_output


# ---------------------------------------------------------------------------
# Test: Resource Management
# ---------------------------------------------------------------------------


class TestResourceManagement:
    """Test resource management under concurrent load."""

    @pytest.mark.asyncio
    async def test_many_concurrent_tools(self, mock_registry, mock_which):
        """Test execution with many concurrent tools."""
        tools = [f"tool_{i}" for i in range(10)]
        executor = ConcurrentToolExecutor(
            tools=tools,
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        call_count = [0]

        async def mock_execute(tool, prompt, cancel_event=None):
            call_count[0] += 1
            await asyncio.sleep(0.01)  # Small delay
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"Output from {tool.name}",
                execution_time=0.01,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert call_count[0] == 10
            assert len(result.tool_results) == 10

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_outputs(self, mock_registry, mock_which):
        """Test handling of large outputs from multiple tools."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        # 10MB output per tool
        large_output = "x" * (10 * 1024 * 1024)

        async def mock_execute(tool, prompt, cancel_event=None):
            return ToolResult(
                tool=tool.name,
                success=True,
                output=large_output,
                execution_time=1.0,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.primary_output) == len(large_output)


# ---------------------------------------------------------------------------
# Test: Mixed Execution Paths
# ---------------------------------------------------------------------------


class TestMixedExecutionPaths:
    """Test mixed provider and direct execution."""

    @pytest.mark.asyncio
    async def test_provider_and_direct_mix(self, mock_which):
        """Test when some tools use providers and others use direct exec."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        # Create mock provider for claude only
        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.is_available.return_value = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Claude via provider"
        mock_result.stderr = ""
        mock_result.return_code = 0
        mock_provider.execute.return_value = mock_result

        # Patch registry to return provider for claude, None for opencode
        original_get = registry.get

        def patched_get(name):
            if name == "claude":
                return mock_provider
            return None

        with patch.object(registry, "get", side_effect=patched_get):
            executor = ConcurrentToolExecutor(
                tools=["claude", "opencode"],
                strategy=AggregationStrategy.ALL_COMPLETE,
            )

            with patch.object(executor, "_execute_direct") as mock_direct:
                mock_direct.return_value = ToolResult(
                    tool="opencode",
                    success=True,
                    output="OpenCode via direct",
                    execution_time=0.1,
                )

                result = await executor.execute("Test prompt")

                # Claude should use provider, opencode should use direct
                mock_provider.execute.assert_called_once()
                mock_direct.assert_called_once()

        ToolProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_provider_unavailable_fallback(self, mock_which):
        """Test fallback to direct execution when provider unavailable."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        mock_provider = MagicMock()
        mock_provider.name = "claude"
        mock_provider.is_available.return_value = False  # Not available

        with patch.object(registry, "get", return_value=mock_provider):
            executor = ConcurrentToolExecutor(
                tools=["claude"],
                strategy=AggregationStrategy.FIRST_SUCCESS,
            )

            with patch.object(executor, "_execute_direct") as mock_direct:
                mock_direct.return_value = ToolResult(
                    tool="claude",
                    success=True,
                    output="Direct execution",
                    execution_time=0.1,
                )

                result = await executor.execute("Test prompt")

                # Should fall back to direct
                mock_direct.assert_called_once()

        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Tool Configuration Variations
# ---------------------------------------------------------------------------


class TestToolConfigurationVariations:
    """Test various tool configuration scenarios."""

    @pytest.mark.asyncio
    async def test_different_timeouts_per_tool(self, mock_registry, mock_which):
        """Test tools with different timeout configurations."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", timeout=60.0),
                ToolConfig(name="opencode", timeout=120.0),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        assert executor.tools[0].timeout == 60.0
        assert executor.tools[1].timeout == 120.0

    @pytest.mark.asyncio
    async def test_weighted_tools(self, mock_registry, mock_which):
        """Test tools with different weights."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", weight=2.0),
                ToolConfig(name="opencode", weight=1.0),
            ],
            strategy=AggregationStrategy.BEST_SCORE,
        )

        assert executor.tools[0].weight == 2.0
        assert executor.tools[1].weight == 1.0

    @pytest.mark.asyncio
    async def test_custom_commands(self, mock_registry, mock_which):
        """Test tools with custom command configurations."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(
                    name="custom_claude",
                    command=["claude", "--custom-flag", "--other"],
                ),
            ],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        assert executor.tools[0].command == ["claude", "--custom-flag", "--other"]


# ---------------------------------------------------------------------------
# Test: Execution Metadata
# ---------------------------------------------------------------------------


class TestExecutionMetadata:
    """Test metadata collection during execution."""

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, mock_registry, mock_which):
        """Test that execution times are tracked per tool."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            await asyncio.sleep(0.05 if tool.name == "claude" else 0.1)
            return ToolResult(
                tool=tool.name,
                success=True,
                output="Output",
                execution_time=0.05 if tool.name == "claude" else 0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Total execution time should be tracked
            assert result.execution_time > 0

            # Individual tool times should be recorded
            for tr in result.tool_results:
                assert tr.execution_time > 0

    @pytest.mark.asyncio
    async def test_scoring_metadata(self, mock_registry, mock_which):
        """Test that scoring metadata is recorded."""
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
                    ToolResult(tool="claude", success=True, output="A" * 500, execution_time=20.0),
                    ToolResult(
                        tool="opencode", success=True, output="B" * 100, execution_time=50.0
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert "scores" in result.metadata
            assert "claude" in result.metadata["scores"]
            assert "opencode" in result.metadata["scores"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
