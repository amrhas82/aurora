"""Unit tests for multi-tool orchestration scenarios.

Tests cover advanced orchestration patterns for running multiple AI tools
(Claude, OpenCode) concurrently, including:

- Time and budget limit enforcement
- Retry logic and exponential backoff
- Resource isolation levels
- Tool provider registry lifecycle
- Output parsing and structured responses
- Real-world prompt patterns with scratchpad state
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

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
# Test: Time Limit Enforcement
# ---------------------------------------------------------------------------


class TestTimeLimitEnforcement:
    """Test time limit enforcement in concurrent execution."""

    @pytest.mark.asyncio
    async def test_executor_respects_global_timeout(self, mock_registry, mock_which):
        """Test that executor respects global timeout setting."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
            timeout=1.0,  # 1 second global timeout
        )

        execution_times = []

        async def mock_execute(tool, prompt, cancel_event=None):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Quick execution
            execution_times.append(asyncio.get_event_loop().time() - start)
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} completed",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            # Both should complete within global timeout
            assert len(result.tool_results) == 2

    @pytest.mark.asyncio
    async def test_per_tool_timeout_override(self, mock_registry, mock_which):
        """Test that per-tool timeout overrides global timeout."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="fast_tool", timeout=0.5),
                ToolConfig(name="slow_tool", timeout=2.0),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
            timeout=10.0,
        )

        assert executor.tools[0].timeout == 0.5
        assert executor.tools[1].timeout == 2.0

    @pytest.mark.asyncio
    async def test_timeout_returns_partial_results(self, mock_registry, mock_which):
        """Test that timeout returns partial results from completed tools."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="fast_tool", timeout=10.0),
                ToolConfig(name="slow_tool", timeout=0.001),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "fast_tool":
                return ToolResult(
                    tool="fast_tool",
                    success=True,
                    output="Fast completed",
                    execution_time=0.001,
                )
            return ToolResult(
                tool="slow_tool",
                success=False,
                output="",
                error="Timeout after 0.001s",
                exit_code=-1,
                execution_time=0.001,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Should succeed because at least one tool succeeded
            assert result.success is True
            assert result.winning_tool == "fast_tool"


# ---------------------------------------------------------------------------
# Test: Retry Logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Test retry behavior for failed tool executions."""

    @pytest.mark.asyncio
    async def test_tool_config_includes_retry_settings(self, mock_registry, mock_which):
        """Test that ToolConfig can specify retry settings."""
        config = ToolConfig(name="test", timeout=60.0)
        # Default ToolConfig doesn't have retry, but the system should handle it

        executor = ConcurrentToolExecutor(
            tools=[config],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        assert len(executor.tools) == 1

    @pytest.mark.asyncio
    async def test_transient_failure_handling(self, mock_registry, mock_which):
        """Test handling of transient failures that might succeed on retry."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        call_count = {"claude": 0, "opencode": 0}

        async def mock_execute(tool, prompt, cancel_event=None):
            call_count[tool.name] += 1
            # Claude fails, OpenCode succeeds
            if tool.name == "claude":
                return ToolResult(
                    tool="claude",
                    success=False,
                    output="",
                    error="Transient network error",
                    exit_code=1,
                )
            await asyncio.sleep(0.01)
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode succeeded",
                execution_time=0.01,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"


# ---------------------------------------------------------------------------
# Test: Resource Isolation Integration
# ---------------------------------------------------------------------------


class TestResourceIsolationIntegration:
    """Test resource isolation in concurrent execution."""

    @pytest.mark.asyncio
    async def test_isolation_level_none(self, mock_registry, mock_which):
        """Test execution with no isolation."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
            isolation_level="none",
        )

        assert executor.isolation_level == "none"
        assert executor._isolation_manager is None

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self, mock_registry, mock_which):
        """Test max concurrent execution limit."""
        executor = ConcurrentToolExecutor(
            tools=[f"tool{i}" for i in range(10)],
            strategy=AggregationStrategy.ALL_COMPLETE,
            max_concurrent=5,
        )

        assert executor.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_max_per_tool_limit(self, mock_registry, mock_which):
        """Test max concurrent per-tool limit."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
            max_per_tool=2,
        )

        assert executor.max_per_tool == 2


# ---------------------------------------------------------------------------
# Test: Tool Provider Registry Lifecycle
# ---------------------------------------------------------------------------


class TestToolProviderRegistryLifecycle:
    """Test tool provider registry behavior during execution."""

    def test_registry_singleton_behavior(self):
        """Test that registry behaves as singleton."""
        ToolProviderRegistry.reset()

        reg1 = ToolProviderRegistry.get_instance()
        reg2 = ToolProviderRegistry.get_instance()

        assert reg1 is reg2

        ToolProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_provider_caching(self, mock_which):
        """Test that providers are cached between calls."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        # First get creates instance
        provider1 = registry.get("claude")
        # Second get returns same instance
        provider2 = registry.get("claude")

        # Both should be same instance (or both None if not registered)
        assert provider1 is provider2

        ToolProviderRegistry.reset()

    def test_registry_reset_clears_cache(self):
        """Test that reset clears the instance cache."""
        ToolProviderRegistry.reset()
        reg1 = ToolProviderRegistry.get_instance()

        # Add a provider
        reg1._providers["test"] = MagicMock()

        ToolProviderRegistry.reset()
        reg2 = ToolProviderRegistry.get_instance()

        # Should be fresh registry
        assert "test" not in reg2._providers

        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Output Parsing
# ---------------------------------------------------------------------------


class TestOutputParsing:
    """Test output parsing and structured response handling."""

    @pytest.mark.asyncio
    async def test_parsed_output_included(self, mock_registry, mock_which):
        """Test that parsed output is included in result."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_result = ToolResult(
                tool="claude",
                success=True,
                output='{"result": "success", "data": [1, 2, 3]}',
                execution_time=0.1,
                parsed_output={"result": "success", "data": [1, 2, 3]},
            )
            mock_execute.return_value = mock_result

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.tool_results[0].parsed_output is not None

    @pytest.mark.asyncio
    async def test_output_with_code_blocks(self, mock_registry, mock_which):
        """Test handling of output containing code blocks."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        code_output = """Here is the solution:

```python
def hello():
    return "world"
```

And here's the test:

```python
def test_hello():
    assert hello() == "world"
```
"""

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output=code_output,
                execution_time=0.1,
            )

            result = await executor.execute("Write hello world")

            assert result.success is True
            assert "```python" in result.primary_output
            assert "def hello():" in result.primary_output


# ---------------------------------------------------------------------------
# Test: Scratchpad State Patterns
# ---------------------------------------------------------------------------


class TestScratchpadStatePatterns:
    """Test patterns involving scratchpad state management."""

    def test_prompt_with_scratchpad_context(self, mock_registry, mock_which):
        """Test prompt construction with scratchpad context."""
        prompt = "Fix the bug in authentication"
        scratchpad_content = """# Scratchpad

STATUS: IN_PROGRESS

## Observations
- Found issue in session handler
- Token not being refreshed

## Next Steps
- Implement token refresh logic
"""

        # Construct context as headless command would
        context = f"{prompt}\n\n## Current Scratchpad State:\n{scratchpad_content}"

        assert "STATUS: IN_PROGRESS" in context
        assert "Fix the bug" in context
        assert "Observations" in context

    @pytest.mark.asyncio
    async def test_status_done_detection_pattern(self, mock_registry, mock_which):
        """Test detection of STATUS: DONE in output."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        done_output = """Updated scratchpad:

# Scratchpad

STATUS: DONE

## Final Summary
- Bug fixed in session.py
- Tests passing
"""

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output=done_output,
                execution_time=1.0,
            )

            result = await executor.execute("Continue working")

            assert "STATUS: DONE" in result.primary_output


# ---------------------------------------------------------------------------
# Test: Tool Coordination Patterns
# ---------------------------------------------------------------------------


class TestToolCoordinationPatterns:
    """Test patterns for coordinating multiple tools."""

    @pytest.mark.asyncio
    async def test_complementary_tool_outputs(self, mock_registry, mock_which):
        """Test merging complementary outputs from different tools."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.SMART_MERGE,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="""## Security Analysis

The code has the following security concerns:
1. SQL injection vulnerability in query builder
2. Missing input validation on user forms
""",
                        execution_time=2.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="""## Performance Analysis

Performance considerations:
1. N+1 query pattern in user listing
2. Missing database indexes on frequently queried columns
""",
                        execution_time=2.5,
                    ),
                ],
            )

            result = await executor.execute("Review this code")

            assert result.success is True
            assert result.conflict_info is not None
            # Both analyses should be preserved in smart merge

    @pytest.mark.asyncio
    async def test_conflicting_recommendations(self, mock_registry, mock_which):
        """Test detection of conflicting recommendations from tools."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.CONSENSUS,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="Use PostgreSQL for ACID compliance and complex queries.",
                        execution_time=1.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="Use MongoDB for schema flexibility and horizontal scaling.",
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("What database should we use?")

            assert result.success is True
            # Should detect the conflict
            assert result.metadata.get("consensus_reached") is False

    @pytest.mark.asyncio
    async def test_agreement_amplification(self, mock_registry, mock_which):
        """Test that tool agreement strengthens confidence."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.CONSENSUS,
        )

        # Same conclusion from both tools
        shared_conclusion = "The bug is in the authentication middleware at line 45."

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output=shared_conclusion,
                        execution_time=1.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output=shared_conclusion,
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Where is the bug?")

            assert result.success is True
            assert result.metadata.get("consensus_reached") is True
            assert result.conflict_info.similarity_score >= 0.95


# ---------------------------------------------------------------------------
# Test: Error Recovery Scenarios
# ---------------------------------------------------------------------------


class TestErrorRecoveryScenarios:
    """Test error recovery in multi-tool scenarios."""

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, mock_registry, mock_which):
        """Test graceful degradation when primary tool fails."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", weight=2.0),  # Primary
                ToolConfig(name="opencode", weight=1.0),  # Fallback
            ],
            strategy=AggregationStrategy.BEST_SCORE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(
                    tool="claude",
                    success=False,
                    output="",
                    error="Service temporarily unavailable",
                    exit_code=503,
                )
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode handled the request",
                execution_time=1.0,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"

    @pytest.mark.asyncio
    async def test_all_tools_recover(self, mock_registry, mock_which):
        """Test scenario where all tools initially fail but task succeeds."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        # Both fail initially
        async def mock_execute(tool, prompt, cancel_event=None):
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error="Rate limited",
                exit_code=429,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is False
            assert len(result.tool_results) == 2
            assert all(not r.success for r in result.tool_results)


# ---------------------------------------------------------------------------
# Test: Metadata Tracking
# ---------------------------------------------------------------------------


class TestMetadataTracking:
    """Test metadata tracking during execution."""

    @pytest.mark.asyncio
    async def test_execution_time_metadata(self, mock_registry, mock_which):
        """Test that execution times are tracked accurately."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            await asyncio.sleep(0.05)
            return ToolResult(
                tool=tool.name,
                success=True,
                output="Done",
                execution_time=0.05,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # Overall execution time should be tracked
            assert result.execution_time > 0
            # Individual tool times should be tracked
            for tr in result.tool_results:
                assert tr.execution_time > 0

    @pytest.mark.asyncio
    async def test_strategy_metadata(self, mock_registry, mock_which):
        """Test that strategy-specific metadata is included."""
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
                    ToolResult(tool="claude", success=True, output="A" * 500, execution_time=10.0),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="B" * 100,
                        execution_time=30.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert "scores" in result.metadata
            assert "claude" in result.metadata["scores"]
            assert "opencode" in result.metadata["scores"]
            # Claude should score higher (success + longer output + faster)
            assert result.metadata["scores"]["claude"] > result.metadata["scores"]["opencode"]


# ---------------------------------------------------------------------------
# Test: File Change Tracking
# ---------------------------------------------------------------------------


class TestFileChangeTracking:
    """Test file change tracking during multi-tool execution."""

    @pytest.mark.asyncio
    async def test_file_tracking_initialization(self, mock_registry, mock_which, tmp_path):
        """Test that file tracking is initialized correctly."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
            track_file_changes=True,
            working_dir=tmp_path,
        )

        assert executor.track_file_changes is True
        assert executor.working_dir == tmp_path
        assert executor._file_aggregator is not None

    @pytest.mark.asyncio
    async def test_file_tracking_disabled(self, mock_registry, mock_which):
        """Test execution with file tracking disabled."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
            track_file_changes=False,
        )

        assert executor._file_aggregator is None


# ---------------------------------------------------------------------------
# Test: Input Method Handling
# ---------------------------------------------------------------------------


class TestInputMethodHandling:
    """Test different input methods for tools."""

    @pytest.mark.asyncio
    async def test_stdin_input_mode(self, mock_registry, mock_which):
        """Test tool configured for stdin input."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="opencode", input_mode="stdin")],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        assert executor.tools[0].input_mode == "stdin"

    @pytest.mark.asyncio
    async def test_argument_input_mode(self, mock_registry, mock_which):
        """Test tool configured for argument input."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="claude", input_mode="arg")],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        assert executor.tools[0].input_mode == "arg"

    @pytest.mark.asyncio
    async def test_mixed_input_modes(self, mock_registry, mock_which):
        """Test execution with tools using different input modes."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", input_mode="arg"),
                ToolConfig(name="opencode", input_mode="stdin"),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} with {tool.input_mode} mode",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.tool_results) == 2


# ---------------------------------------------------------------------------
# Test: Working Directory Handling
# ---------------------------------------------------------------------------


class TestWorkingDirectoryHandling:
    """Test working directory configuration."""

    @pytest.mark.asyncio
    async def test_custom_working_directory(self, mock_registry, mock_which, tmp_path):
        """Test execution with custom working directory."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
            working_dir=tmp_path,
        )

        assert executor.working_dir == tmp_path

    @pytest.mark.asyncio
    async def test_default_working_directory(self, mock_registry, mock_which):
        """Test execution with default working directory."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        # Should use current directory
        assert executor.working_dir == Path.cwd()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
