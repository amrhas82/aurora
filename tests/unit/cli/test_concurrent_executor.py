"""Unit tests for ConcurrentToolExecutor.

Tests cover:
- Basic parallel execution with multiple tools
- All aggregation strategies (first_success, all_complete, voting, best_score, merge)
- Timeout and cancellation handling
- Error handling and mixed success/failure scenarios
- Tool provider integration
- Custom scorer functions
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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
    run_concurrent,
)
from aurora_cli.tool_providers import ToolProviderRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_registry():
    """Create mock ToolProviderRegistry that returns no providers."""
    # Reset registry to clean state
    ToolProviderRegistry.reset()
    registry = ToolProviderRegistry.get_instance()
    # Clear built-in providers so get() returns None
    registry._providers = {}
    registry._instances = {}
    yield registry
    ToolProviderRegistry.reset()


@pytest.fixture
def mock_which():
    """Mock shutil.which to report tools as available."""
    with patch("aurora_cli.concurrent_executor.shutil.which") as mock:
        mock.return_value = "/usr/bin/tool"
        yield mock


@pytest.fixture
def executor_with_mocks(mock_registry, mock_which):
    """Create executor with mocked dependencies."""
    return ConcurrentToolExecutor(
        tools=["claude", "opencode"],
        strategy=AggregationStrategy.FIRST_SUCCESS,
    )


# ---------------------------------------------------------------------------
# Test: Tool Configuration
# ---------------------------------------------------------------------------


class TestToolConfiguration:
    """Test tool configuration and normalization."""

    def test_normalize_string_tools(self, mock_registry, mock_which):
        """Test that string tool names are converted to ToolConfig."""
        executor = ConcurrentToolExecutor(tools=["claude", "opencode"])

        assert len(executor.tools) == 2
        assert all(isinstance(t, ToolConfig) for t in executor.tools)
        assert executor.tools[0].name == "claude"
        assert executor.tools[1].name == "opencode"

    def test_normalize_tool_configs(self, mock_registry, mock_which):
        """Test that ToolConfig objects are preserved."""
        configs = [
            ToolConfig(name="claude", timeout=300.0, weight=2.0),
            ToolConfig(name="opencode", timeout=600.0, weight=1.0),
        ]
        executor = ConcurrentToolExecutor(tools=configs)

        assert executor.tools[0].timeout == 300.0
        assert executor.tools[0].weight == 2.0
        assert executor.tools[1].timeout == 600.0

    def test_mixed_tools(self, mock_registry, mock_which):
        """Test mixing string and ToolConfig tools."""
        executor = ConcurrentToolExecutor(
            tools=["claude", ToolConfig(name="opencode", timeout=300.0)],
        )

        assert executor.tools[0].name == "claude"
        assert executor.tools[0].timeout == 600.0  # default
        assert executor.tools[1].name == "opencode"
        assert executor.tools[1].timeout == 300.0

    def test_validate_tools_missing(self, mock_registry):
        """Test validation fails for missing tools."""
        with patch("aurora_cli.concurrent_executor.shutil.which", return_value=None):
            with pytest.raises(ValueError, match="Tools not found in PATH"):
                ConcurrentToolExecutor(tools=["nonexistent_tool"])

    def test_validate_tools_with_provider(self, mock_which):
        """Test validation passes when provider is available."""
        # Use the real registry with built-in providers
        ToolProviderRegistry.reset()

        with patch("shutil.which", return_value="/usr/bin/claude"):
            # Should not raise because claude provider is registered
            executor = ConcurrentToolExecutor(tools=["claude"])
            assert len(executor.tools) == 1

        ToolProviderRegistry.reset()

    def test_disabled_tools_skip_validation(self, mock_registry, mock_which):
        """Test that disabled tools are not validated."""
        mock_which.return_value = None  # Tool not in PATH

        executor = ConcurrentToolExecutor(tools=[ToolConfig(name="disabled_tool", enabled=False)])

        # Should not raise despite tool not being available
        assert len(executor.tools) == 1
        assert not executor.tools[0].enabled


# ---------------------------------------------------------------------------
# Test: Basic Execution
# ---------------------------------------------------------------------------


class TestBasicExecution:
    """Test basic tool execution."""

    @pytest.mark.asyncio
    async def test_execute_single_tool(self, mock_registry, mock_which):
        """Test executing with a single tool."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Test output",
                execution_time=1.5,
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.primary_output == "Test output"
            assert result.winning_tool == "claude"
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_tools(self, mock_registry, mock_which):
        """Test executing with multiple tools in parallel."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.side_effect = [
                ToolResult(tool="claude", success=True, output="Claude output", execution_time=1.0),
                ToolResult(
                    tool="opencode",
                    success=True,
                    output="OpenCode output more text",
                    execution_time=2.0,
                ),
            ]

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.tool_results) == 2
            # OpenCode has longer output, should win
            assert result.winning_tool == "opencode"

    @pytest.mark.asyncio
    async def test_execute_no_enabled_tools(self, mock_registry, mock_which):
        """Test execution with no enabled tools."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="claude", enabled=False)],
        )

        result = await executor.execute("Test prompt")

        assert result.success is False
        assert "No tools enabled" in result.metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_execute_tracking_time(self, mock_registry, mock_which):
        """Test that execution time is tracked."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Output",
                execution_time=0.5,
            )

            result = await executor.execute("Test prompt")

            assert result.execution_time > 0


# ---------------------------------------------------------------------------
# Test: Aggregation Strategies
# ---------------------------------------------------------------------------


class TestFirstSuccessStrategy:
    """Test FIRST_SUCCESS aggregation strategy."""

    @pytest.mark.asyncio
    async def test_returns_first_success(self, mock_registry, mock_which):
        """Test that first successful result is returned."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        call_order = []

        async def mock_execute(tool, prompt, cancel_event=None):
            call_order.append(tool.name)
            if tool.name == "claude":
                await asyncio.sleep(0.01)  # Claude is faster
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Claude first",
                    execution_time=0.01,
                )
            await asyncio.sleep(0.1)
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "claude"
            assert result.primary_output == "Claude first"

    @pytest.mark.asyncio
    async def test_skips_failures_for_success(self, mock_registry, mock_which):
        """Test that failures are skipped until a success is found."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(
                    tool="claude",
                    success=False,
                    output="",
                    error="Failed",
                    execution_time=0.01,
                )
            await asyncio.sleep(0.02)
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode success",
                execution_time=0.02,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"

    @pytest.mark.asyncio
    async def test_all_failures_returns_first(self, mock_registry, mock_which):
        """Test that when all fail, first result is returned."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=False,
                output="Error output",
                error="Failed",
            )

            result = await executor.execute("Test prompt")

            assert result.success is False
            assert "All tools failed" in result.metadata.get("error", "")


class TestAllCompleteStrategy:
    """Test ALL_COMPLETE aggregation strategy."""

    @pytest.mark.asyncio
    async def test_waits_for_all_tools(self, mock_registry, mock_which):
        """Test that all tools complete before result is returned."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        completed_tools = []

        async def mock_execute(tool, prompt, cancel_event=None):
            completed_tools.append(tool.name)
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} output",
                execution_time=0.1,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert len(completed_tools) == 2
            assert "claude" in completed_tools
            assert "opencode" in completed_tools
            assert len(result.tool_results) == 2

    @pytest.mark.asyncio
    async def test_returns_longest_output(self, mock_registry, mock_which):
        """Test that result with longest output wins."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.side_effect = [
                ToolResult(tool="claude", success=True, output="Short", execution_time=0.1),
                ToolResult(
                    tool="opencode",
                    success=True,
                    output="This is a much longer output",
                    execution_time=0.1,
                ),
            ]

            result = await executor.execute("Test prompt")

            assert result.winning_tool == "opencode"

    @pytest.mark.asyncio
    async def test_handles_exceptions(self, mock_registry, mock_which):
        """Test that exceptions are converted to ToolResult."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                raise ValueError("Test exception")
            return ToolResult(tool="opencode", success=True, output="Success", execution_time=0.1)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert len(result.tool_results) == 2
            claude_result = [r for r in result.tool_results if r.tool == "claude"][0]
            assert claude_result.success is False
            assert "Test exception" in claude_result.error


class TestVotingStrategy:
    """Test VOTING aggregation strategy."""

    @pytest.mark.asyncio
    async def test_voting_requires_three_tools(self, mock_registry, mock_which):
        """Test that voting falls back to ALL_COMPLETE with < 3 tools."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.VOTING,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="Output",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[],
            )

            result = await executor.execute("Test prompt")

            mock_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_voting_consensus(self, mock_registry, mock_which):
        """Test voting with consensus (same output from multiple tools)."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor"],
            strategy=AggregationStrategy.VOTING,
        )

        # Mock _execute_all_complete to return results with voting data
        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="Consensus answer",
                        execution_time=0.1,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="Consensus answer",
                        execution_time=0.1,
                    ),
                    ToolResult(
                        tool="cursor",
                        success=True,
                        output="Different answer",
                        execution_time=0.1,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            # Consensus answer should win (2 votes vs 1)
            assert result.success is True
            assert "Consensus answer" in result.primary_output


class TestBestScoreStrategy:
    """Test BEST_SCORE aggregation strategy."""

    @pytest.mark.asyncio
    async def test_default_scorer(self, mock_registry, mock_which):
        """Test default scoring function."""
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
                    ToolResult(tool="claude", success=False, output="Failed", execution_time=1.0),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="A" * 500,
                        execution_time=25.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            # OpenCode should win (success gives 10 points, long output gives 5, fast gives 3)
            assert result.winning_tool == "opencode"
            assert "scores" in result.metadata

    @pytest.mark.asyncio
    async def test_custom_scorer(self, mock_registry, mock_which):
        """Test custom scoring function."""

        def custom_scorer(result: ToolResult) -> float:
            # Prefer Claude regardless of other factors
            return 100.0 if result.tool == "claude" else 0.0

        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.BEST_SCORE,
            scorer=custom_scorer,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=False, output="", execution_time=100.0),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="A" * 1000,
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.winning_tool == "claude"


class TestMergeStrategy:
    """Test MERGE aggregation strategy."""

    @pytest.mark.asyncio
    async def test_merge_outputs(self, mock_registry, mock_which):
        """Test that outputs from all successful tools are merged."""
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
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="Claude's analysis",
                        execution_time=0.1,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="OpenCode's analysis",
                        execution_time=0.1,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert "=== claude ===" in result.primary_output
            assert "Claude's analysis" in result.primary_output
            assert "=== opencode ===" in result.primary_output
            assert "OpenCode's analysis" in result.primary_output
            assert result.metadata.get("merged_count") == 2

    @pytest.mark.asyncio
    async def test_merge_excludes_failures(self, mock_registry, mock_which):
        """Test that failed tools are excluded from merge."""
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
                    ToolResult(tool="claude", success=False, output="Error", execution_time=0.1),
                    ToolResult(tool="opencode", success=True, output="Success", execution_time=0.1),
                ],
            )

            result = await executor.execute("Test prompt")

            assert "=== opencode ===" in result.primary_output
            assert "=== claude ===" not in result.primary_output
            assert result.metadata.get("merged_count") == 1

    @pytest.mark.asyncio
    async def test_merge_all_failures(self, mock_registry, mock_which):
        """Test merge when all tools fail."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.MERGE,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            mock_all.return_value = AggregatedResult(
                success=False,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(tool="claude", success=False, output="Error1", execution_time=0.1),
                    ToolResult(tool="opencode", success=False, output="Error2", execution_time=0.1),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is False
            assert result.primary_output == ""


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_tool_timeout(self, mock_registry, mock_which):
        """Test that tool timeout is handled correctly."""
        executor = ConcurrentToolExecutor(
            tools=[ToolConfig(name="claude", timeout=0.1)],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def slow_execute(tool, prompt, cancel_event=None):
            await asyncio.sleep(1.0)  # Longer than timeout
            return ToolResult(
                tool="claude",
                success=True,
                output="Never reached",
                execution_time=1.0,
            )

        # Need to test the actual timeout mechanism in _execute_direct
        with patch.object(executor, "_execute_direct") as mock_direct:
            mock_direct.return_value = ToolResult(
                tool="claude",
                success=False,
                output="",
                error="Timeout after 0.1s",
                exit_code=-1,
                execution_time=0.1,
            )

            result = await executor.execute("Test prompt")

            assert result.success is False
            assert "Timeout" in result.tool_results[0].error

    @pytest.mark.asyncio
    async def test_cancellation_handling(self, mock_registry, mock_which):
        """Test that cancelled tasks are handled gracefully."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(tool="claude", success=True, output="Quick", execution_time=0.01)
            # Simulate slow tool that gets cancelled
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                return ToolResult(
                    tool="opencode",
                    success=False,
                    output="",
                    error="Cancelled",
                    exit_code=-2,
                )
            return ToolResult(tool="opencode", success=True, output="Slow", execution_time=10.0)

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            # First success should win and cancel the slow one
            assert result.success is True
            assert result.winning_tool == "claude"


# ---------------------------------------------------------------------------
# Test: Default Scorer
# ---------------------------------------------------------------------------


class TestDefaultScorer:
    """Test the default scoring function."""

    def test_success_bonus(self, mock_registry, mock_which):
        """Test that successful results get 10 points."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        success_result = ToolResult(tool="test", success=True, output="", execution_time=120.0)
        failure_result = ToolResult(tool="test", success=False, output="", execution_time=120.0)

        assert executor._default_scorer(success_result) == 10.0
        assert executor._default_scorer(failure_result) == 0.0

    def test_output_length_bonus(self, mock_registry, mock_which):
        """Test output length bonus (max 5 points)."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        short = ToolResult(tool="test", success=False, output="x" * 100, execution_time=120.0)
        medium = ToolResult(tool="test", success=False, output="x" * 300, execution_time=120.0)
        long = ToolResult(tool="test", success=False, output="x" * 1000, execution_time=120.0)

        assert executor._default_scorer(short) == 1.0  # 100/100 = 1
        assert executor._default_scorer(medium) == 3.0  # 300/100 = 3
        assert executor._default_scorer(long) == 5.0  # capped at 5

    def test_speed_bonus(self, mock_registry, mock_which):
        """Test speed bonus."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        fast = ToolResult(tool="test", success=False, output="", execution_time=10.0)
        medium = ToolResult(tool="test", success=False, output="", execution_time=45.0)
        slow = ToolResult(tool="test", success=False, output="", execution_time=90.0)
        very_slow = ToolResult(tool="test", success=False, output="", execution_time=200.0)

        assert executor._default_scorer(fast) == 3.0  # < 30s
        assert executor._default_scorer(medium) == 2.0  # < 60s
        assert executor._default_scorer(slow) == 1.0  # < 120s
        assert executor._default_scorer(very_slow) == 0.0  # >= 120s


# ---------------------------------------------------------------------------
# Test: Synchronous Wrapper
# ---------------------------------------------------------------------------


class TestRunConcurrent:
    """Test the synchronous run_concurrent wrapper."""

    def test_run_concurrent_basic(self, mock_registry, mock_which):
        """Test basic synchronous execution."""
        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_instance = MagicMock()
            MockExecutor.return_value = mock_instance

            # Create a proper coroutine that returns the expected result
            async def mock_execute(prompt):
                return AggregatedResult(
                    success=True,
                    primary_output="Output",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_instance.execute = mock_execute

            result = run_concurrent(
                prompt="Test",
                tools=["claude", "opencode"],
                strategy="first_success",
            )

            assert result.success is True
            MockExecutor.assert_called_once_with(
                ["claude", "opencode"],
                strategy=AggregationStrategy.FIRST_SUCCESS,
                timeout=600.0,
            )


# ---------------------------------------------------------------------------
# Test: Direct Subprocess Execution
# ---------------------------------------------------------------------------


class TestDirectExecution:
    """Test direct subprocess execution fallback."""

    @pytest.mark.asyncio
    async def test_execute_direct_claude(self, mock_registry, mock_which):
        """Test direct execution for Claude tool."""
        executor = ConcurrentToolExecutor(tools=["claude"])
        tool = executor.tools[0]

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Output", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await executor._execute_direct(tool, "Test prompt", 0.0)

            assert result.success is True
            assert result.output == "Output"
            # Verify Claude command structure
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0]
            assert "claude" in call_args
            assert "--print" in call_args
            assert "--dangerously-skip-permissions" in call_args

    @pytest.mark.asyncio
    async def test_execute_direct_opencode(self, mock_registry, mock_which):
        """Test direct execution for OpenCode tool (uses stdin)."""
        executor = ConcurrentToolExecutor(tools=["opencode"])
        tool = executor.tools[0]

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Output", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await executor._execute_direct(tool, "Test prompt", 0.0)

            assert result.success is True
            # Verify stdin was used
            mock_process.communicate.assert_called_once()
            call_args = mock_process.communicate.call_args
            assert call_args[1].get("input") == b"Test prompt"

    @pytest.mark.asyncio
    async def test_execute_direct_timeout(self, mock_registry, mock_which):
        """Test timeout during direct execution."""
        executor = ConcurrentToolExecutor(tools=[ToolConfig(name="claude", timeout=0.001)])
        tool = executor.tools[0]

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_subprocess.return_value = mock_process

            result = await executor._execute_direct(tool, "Test prompt", 0.0)

            assert result.success is False
            assert "Timeout" in result.error
            assert result.exit_code == -1

    @pytest.mark.asyncio
    async def test_execute_direct_cancelled(self, mock_registry, mock_which):
        """Test cancellation during direct execution."""
        executor = ConcurrentToolExecutor(tools=["claude"])
        tool = executor.tools[0]

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.CancelledError()
            mock_subprocess.return_value = mock_process

            result = await executor._execute_direct(tool, "Test prompt", 0.0)

            assert result.success is False
            assert "Cancelled" in result.error
            assert result.exit_code == -2


# ---------------------------------------------------------------------------
# Test: Provider-based Execution
# ---------------------------------------------------------------------------


class TestProviderExecution:
    """Test execution using registered tool providers."""

    @pytest.mark.asyncio
    async def test_execute_with_provider(self, mock_which):
        """Test execution using a registered provider."""
        # Use real registry but with mocked provider
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        # Create mock provider and register it
        mock_provider = MagicMock()
        mock_provider.name = "testprovider"
        mock_provider.is_available.return_value = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Provider output"
        mock_result.stderr = ""
        mock_result.return_code = 0
        mock_provider.execute.return_value = mock_result

        # Patch the registry's get method to return our mock
        with patch.object(registry, "get", return_value=mock_provider):
            executor = ConcurrentToolExecutor(tools=["testprovider"])
            result = await executor._execute_tool(executor.tools[0], "Test prompt")

            assert result.success is True
            assert result.output == "Provider output"
            mock_provider.execute.assert_called_once()

        ToolProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_fallback_to_direct_when_no_provider(self, mock_registry, mock_which):
        """Test fallback to direct execution when no provider registered."""
        # mock_registry fixture clears providers, so get() returns None
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_direct") as mock_direct:
            mock_direct.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Direct output",
                execution_time=0.1,
            )

            result = await executor._execute_tool(executor.tools[0], "Test prompt")

            mock_direct.assert_called_once()
            assert result.output == "Direct output"

    @pytest.mark.asyncio
    async def test_provider_timeout(self, mock_which):
        """Test timeout handling with provider execution."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        mock_provider = MagicMock()
        mock_provider.name = "slowprovider"
        mock_provider.is_available.return_value = True

        # Simulate slow provider
        def slow_execute(*args, **kwargs):
            import time

            time.sleep(1.0)
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.stdout = "Output"
            mock_result.stderr = ""
            mock_result.return_code = 0
            return mock_result

        mock_provider.execute = slow_execute

        with patch.object(registry, "get", return_value=mock_provider):
            executor = ConcurrentToolExecutor(
                tools=[ToolConfig(name="slowprovider", timeout=0.01)],
            )

            result = await executor._execute_with_provider(
                mock_provider,
                executor.tools[0],
                "Test prompt",
                0.0,
            )

            # Should timeout
            assert result.success is False
            assert "Timeout" in result.error

        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_output(self, mock_registry, mock_which):
        """Test handling of empty output."""
        executor = ConcurrentToolExecutor(
            tools=["claude"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="",
                execution_time=0.1,
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.primary_output == ""

    @pytest.mark.asyncio
    async def test_unicode_output(self, mock_registry, mock_which):
        """Test handling of Unicode output."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output="Hello World",
                execution_time=0.1,
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert "World" in result.primary_output

    @pytest.mark.asyncio
    async def test_very_large_output(self, mock_registry, mock_which):
        """Test handling of very large output."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        large_output = "x" * 100000  # 100KB

        with patch.object(executor, "_execute_tool") as mock_execute:
            mock_execute.return_value = ToolResult(
                tool="claude",
                success=True,
                output=large_output,
                execution_time=0.1,
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.primary_output) == 100000

    def test_unknown_strategy(self, mock_registry, mock_which):
        """Test handling of unknown strategy."""
        with pytest.raises(ValueError):
            AggregationStrategy("unknown_strategy")


# ---------------------------------------------------------------------------
# Test: Conflict Detection
# ---------------------------------------------------------------------------


class TestConflictDetector:
    """Test conflict detection between tool outputs."""

    def test_identical_outputs_no_conflict(self):
        """Test that identical outputs show no conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello world"),
            ToolResult(tool="opencode", success=True, output="Hello world"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE
        assert conflict.similarity_score >= 0.95

    def test_similar_outputs_minor_conflict(self):
        """Test that similar outputs show minor conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello world! This is a test."),
            ToolResult(tool="opencode", success=True, output="Hello world! This is test."),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity in (ConflictSeverity.NONE, ConflictSeverity.MINOR)
        assert conflict.similarity_score >= 0.8

    def test_different_outputs_major_conflict(self):
        """Test that very different outputs show major conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42."),
            ToolResult(tool="opencode", success=True, output="I don't know the answer."),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)
        assert conflict.similarity_score < 0.6

    def test_formatting_only_differences(self):
        """Test that whitespace-only differences are detected as formatting."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello   world\n\n\ntest"),
            ToolResult(tool="opencode", success=True, output="Hello world\n\ntest"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        # After normalization, these should be similar
        assert conflict.similarity_score >= 0.85

    def test_single_result_no_conflict(self):
        """Test that single result shows no conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello world"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE
        assert conflict.similarity_score == 1.0

    def test_normalize_output(self):
        """Test output normalization."""
        text = "  Hello   world  \n\n\n  test  "
        normalized = ConflictDetector.normalize_output(text)
        assert "  " not in normalized or normalized == "Hello world test"

    def test_extract_code_blocks(self):
        """Test code block extraction."""
        text = "Here is code:\n```python\nprint('hello')\n```\nAnd more:\n```js\nconsole.log('hi')\n```"
        blocks = ConflictDetector.extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[1][0] == "js"


class TestConflictResolver:
    """Test conflict resolution strategies."""

    def test_consensus_reached(self):
        """Test consensus resolution when agreement exists."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42"),
            ToolResult(tool="opencode", success=True, output="The answer is 42"),
        ]
        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.8)
        assert winner is not None
        assert winner.output == "The answer is 42"
        assert conflict_info.similarity_score >= 0.8

    def test_consensus_not_reached(self):
        """Test consensus resolution when no agreement."""
        results = [
            ToolResult(tool="claude", success=True, output="Yes, definitely."),
            ToolResult(tool="opencode", success=True, output="No, never."),
        ]
        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.8)
        assert winner is None
        assert conflict_info.similarity_score < 0.8

    def test_weighted_vote_uses_weights(self):
        """Test that weighted voting respects tool weights."""
        results = [
            ToolResult(tool="claude", success=True, output="A", execution_time=10),
            ToolResult(tool="opencode", success=True, output="B", execution_time=10),
        ]
        weights = {"claude": 2.0, "opencode": 1.0}
        winner, _ = ConflictResolver.resolve_by_weighted_vote(results, weights)
        assert winner.tool == "claude"

    def test_smart_merge_similar_outputs(self):
        """Test smart merge with similar outputs just uses best."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello world"),
            ToolResult(tool="opencode", success=True, output="Hello world"),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        # Should just use the longer/same output, not add merge header
        assert "Merged Output" not in merged
        assert "Hello world" in merged

    def test_smart_merge_different_outputs(self):
        """Test smart merge with different outputs adds header."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="First unique content here that is long enough.",
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="Second unique content here that is different.",
            ),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        if conflict_info.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR):
            assert "Merged Output" in merged


# ---------------------------------------------------------------------------
# Test: Smart Merge Strategy
# ---------------------------------------------------------------------------


class TestSmartMergeStrategy:
    """Test smart merge aggregation strategy."""

    @pytest.mark.asyncio
    async def test_smart_merge_returns_conflict_info(self, mock_registry, mock_which):
        """Test that smart merge includes conflict info."""
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
                    ToolResult(tool="claude", success=True, output="Output A"),
                    ToolResult(tool="opencode", success=True, output="Output B"),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.strategy_used == AggregationStrategy.SMART_MERGE
            assert result.conflict_info is not None
            assert "conflict_severity" in result.metadata
            assert "similarity_score" in result.metadata


# ---------------------------------------------------------------------------
# Test: Consensus Strategy
# ---------------------------------------------------------------------------


class TestConsensusStrategy:
    """Test consensus aggregation strategy."""

    @pytest.mark.asyncio
    async def test_consensus_with_agreement(self, mock_registry, mock_which):
        """Test consensus strategy when tools agree."""
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
                    ToolResult(tool="claude", success=True, output="Same answer"),
                    ToolResult(tool="opencode", success=True, output="Same answer"),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.strategy_used == AggregationStrategy.CONSENSUS
            assert result.success is True
            assert result.metadata.get("consensus_reached") is True

    @pytest.mark.asyncio
    async def test_consensus_with_disagreement(self, mock_registry, mock_which):
        """Test consensus strategy when tools disagree."""
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
                    ToolResult(tool="claude", success=True, output="Yes", execution_time=1.0),
                    ToolResult(tool="opencode", success=True, output="No", execution_time=1.0),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.strategy_used == AggregationStrategy.CONSENSUS
            assert result.metadata.get("consensus_reached") is False
            assert result.metadata.get("resolution_method") == "weighted_vote"
            assert result.conflict_info is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
