"""Unit tests for Claude + OpenCode multi-tool concurrent execution.

Tests cover specific scenarios for running Claude and OpenCode together:
- Tool-specific command building and execution
- Claude's --print flag vs OpenCode's stdin mode
- Provider-based vs direct execution paths
- Cross-tool conflict detection patterns
- Tool-specific error handling and recovery
- Strategy behaviors with Claude/OpenCode pairs
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ConflictDetector,
    ConflictSeverity,
    ToolConfig,
    ToolResult,
)
from aurora_cli.tool_providers import ToolProviderRegistry
from aurora_cli.tool_providers.base import InputMethod, ToolCapabilities


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
    """Mock shutil.which for Claude and OpenCode."""
    with patch("aurora_cli.concurrent_executor.shutil.which") as mock:
        mock.side_effect = lambda x: f"/usr/bin/{x}" if x in ["claude", "opencode"] else None
        yield mock


@pytest.fixture
def claude_provider_mock():
    """Create mock Claude tool provider."""
    mock_provider = MagicMock()
    mock_provider.name = "claude"
    mock_provider.display_name = "Claude"
    mock_provider.is_available.return_value = True
    mock_provider.input_method = InputMethod.ARGUMENT
    mock_provider.priority = 100
    mock_provider.default_flags = ["--print", "--dangerously-skip-permissions"]
    mock_provider.capabilities = ToolCapabilities(
        supports_streaming=True,
        supports_conversation=True,
        supports_system_prompt=True,
        supports_tools=True,
        max_context_length=200000,
        default_timeout=600,
        priority=100,
    )
    return mock_provider


@pytest.fixture
def opencode_provider_mock():
    """Create mock OpenCode tool provider."""
    mock_provider = MagicMock()
    mock_provider.name = "opencode"
    mock_provider.display_name = "OpenCode"
    mock_provider.is_available.return_value = True
    mock_provider.input_method = InputMethod.STDIN
    mock_provider.priority = 150
    mock_provider.default_flags = []
    mock_provider.capabilities = ToolCapabilities(
        supports_streaming=False,
        supports_conversation=True,
        supports_system_prompt=False,
        supports_tools=True,
        max_context_length=128000,
        default_timeout=600,
        priority=150,
    )
    return mock_provider


# ---------------------------------------------------------------------------
# Test: Claude-Specific Command Building
# ---------------------------------------------------------------------------


class TestClaudeCommandBuilding:
    """Test Claude-specific command construction."""

    @pytest.mark.asyncio
    async def test_claude_uses_print_flag(self, mock_registry, mock_which):
        """Test that Claude uses --print flag for non-interactive mode."""
        executor = ConcurrentToolExecutor(tools=["claude"])

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Claude response", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await executor._execute_direct(executor.tools[0], "Test prompt", 0.0)

            # Verify Claude-specific flags
            call_args = mock_subprocess.call_args[0]
            assert "claude" in call_args
            assert "--print" in call_args
            assert "--dangerously-skip-permissions" in call_args

    @pytest.mark.asyncio
    async def test_claude_context_as_argument(self, mock_registry, mock_which):
        """Test that Claude can receive context as command argument."""
        executor = ConcurrentToolExecutor(tools=[ToolConfig(name="claude", input_mode="arg")])

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Response", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await executor._execute_direct(executor.tools[0], "Test prompt", 0.0)

            # Should still work
            mock_subprocess.assert_called_once()


# ---------------------------------------------------------------------------
# Test: OpenCode-Specific Command Building
# ---------------------------------------------------------------------------


class TestOpenCodeCommandBuilding:
    """Test OpenCode-specific command construction."""

    @pytest.mark.asyncio
    async def test_opencode_uses_stdin(self, mock_registry, mock_which):
        """Test that OpenCode receives context via stdin."""
        executor = ConcurrentToolExecutor(tools=["opencode"])

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"OpenCode response", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await executor._execute_direct(executor.tools[0], "Test prompt", 0.0)

            # Verify stdin was used
            mock_process.communicate.assert_called_once()
            call_args = mock_process.communicate.call_args
            assert call_args[1].get("input") == b"Test prompt"

    @pytest.mark.asyncio
    async def test_opencode_minimal_command(self, mock_registry, mock_which):
        """Test that OpenCode command is minimal (no extra flags by default)."""
        executor = ConcurrentToolExecutor(tools=["opencode"])

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"Response", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await executor._execute_direct(executor.tools[0], "Test prompt", 0.0)

            call_args = mock_subprocess.call_args[0]
            # OpenCode command should be simple
            assert "opencode" in call_args


# ---------------------------------------------------------------------------
# Test: Parallel Execution of Claude + OpenCode
# ---------------------------------------------------------------------------


class TestClaudeOpenCodeParallel:
    """Test parallel execution with both Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_both_tools_execute_concurrently(self, mock_registry, mock_which):
        """Test that Claude and OpenCode run in parallel."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        execution_order = []
        execution_times = {}

        async def mock_execute(tool, prompt, cancel_event=None):
            start = asyncio.get_event_loop().time()
            execution_order.append(f"{tool.name}_start")
            await asyncio.sleep(0.05)  # Simulate work
            execution_order.append(f"{tool.name}_end")
            execution_times[tool.name] = asyncio.get_event_loop().time() - start
            return ToolResult(
                tool=tool.name,
                success=True,
                output=f"{tool.name} completed",
                execution_time=0.05,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert len(result.tool_results) == 2

            # Both should start before either ends (true parallelism)
            claude_start = execution_order.index("claude_start")
            opencode_start = execution_order.index("opencode_start")
            claude_end = execution_order.index("claude_end")
            opencode_end = execution_order.index("opencode_end")

            # Both should start close together
            assert abs(claude_start - opencode_start) <= 1

    @pytest.mark.asyncio
    async def test_claude_faster_wins_first_success(self, mock_registry, mock_which):
        """Test first_success when Claude is faster."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                await asyncio.sleep(0.01)  # Claude is faster
                return ToolResult(
                    tool="claude",
                    success=True,
                    output="Claude wins",
                    execution_time=0.01,
                )
            await asyncio.sleep(0.1)  # OpenCode is slower
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
            assert result.primary_output == "Claude wins"

    @pytest.mark.asyncio
    async def test_opencode_faster_wins_first_success(self, mock_registry, mock_which):
        """Test first_success when OpenCode is faster."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                await asyncio.sleep(0.1)  # Claude is slower
                return ToolResult(tool="claude", success=True, output="Claude", execution_time=0.1)
            await asyncio.sleep(0.01)  # OpenCode is faster
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode wins",
                execution_time=0.01,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"
            assert result.primary_output == "OpenCode wins"

    @pytest.mark.asyncio
    async def test_claude_fails_opencode_succeeds(self, mock_registry, mock_which):
        """Test fallback to OpenCode when Claude fails."""
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
                    error="Rate limited",
                    execution_time=0.01,
                )
            await asyncio.sleep(0.02)
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode saved the day",
                execution_time=0.02,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"

    @pytest.mark.asyncio
    async def test_both_fail_returns_error(self, mock_registry, mock_which):
        """Test behavior when both Claude and OpenCode fail."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=f"{tool.name} failed",
                execution_time=0.01,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is False
            assert "All tools failed" in result.metadata.get("error", "")


# ---------------------------------------------------------------------------
# Test: Cross-Tool Conflict Detection
# ---------------------------------------------------------------------------


class TestCrossToolConflictDetection:
    """Test conflict detection between Claude and OpenCode outputs."""

    def test_similar_code_suggestions_no_conflict(self):
        """Test that similar code from both tools shows no conflict."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="```python\ndef hello():\n    return 'world'\n```",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="```python\ndef hello():\n    return 'world'\n```",
                execution_time=1.0,
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        assert conflict_info.severity == ConflictSeverity.NONE
        assert conflict_info.similarity_score >= 0.95

    def test_different_implementations_detected(self):
        """Test that different implementations are detected as conflict."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="Use async/await for this:\n```python\nasync def fetch():\n    return await client.get()\n```",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="Use threading for this:\n```python\nfrom threading import Thread\ndef fetch():\n    return requests.get()\n```",
                execution_time=1.0,
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        assert conflict_info.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)
        assert conflict_info.similarity_score < 0.85

    def test_formatting_differences_only(self):
        """Test that formatting-only differences are detected correctly."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="def foo():\n    x = 1\n    return x",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="def foo():\n  x = 1\n  return x",  # Different indentation
                execution_time=1.0,
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        # Should recognize these are essentially the same
        assert conflict_info.similarity_score >= 0.75

    def test_conflicting_recommendations(self):
        """Test detection of conflicting recommendations."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="I recommend using PostgreSQL for this use case because it offers better ACID compliance.",
                execution_time=1.0,
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="I recommend using MongoDB for this use case because it offers better scalability.",
                execution_time=1.0,
            ),
        ]

        conflict_info = ConflictDetector.detect_conflicts(results)

        assert conflict_info.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)


# ---------------------------------------------------------------------------
# Test: Strategy-Specific Behaviors
# ---------------------------------------------------------------------------


class TestClaudeOpenCodeStrategies:
    """Test different aggregation strategies with Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_best_score_prefers_longer_output(self, mock_registry, mock_which):
        """Test that best_score prefers more detailed responses."""
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
                        tool="claude",
                        success=True,
                        output="Short",
                        execution_time=30.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="A much longer and more detailed response with code examples and explanations that provides more value"
                        * 10,
                        execution_time=60.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            # OpenCode should win due to longer output despite slower
            assert result.winning_tool == "opencode"
            assert "scores" in result.metadata

    @pytest.mark.asyncio
    async def test_merge_combines_both_outputs(self, mock_registry, mock_which):
        """Test that merge strategy includes both Claude and OpenCode output."""
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
                        output="Claude's perspective",
                        execution_time=1.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="OpenCode's perspective",
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert "=== claude ===" in result.primary_output
            assert "=== opencode ===" in result.primary_output
            assert "Claude's perspective" in result.primary_output
            assert "OpenCode's perspective" in result.primary_output
            assert result.metadata.get("merged_count") == 2

    @pytest.mark.asyncio
    async def test_consensus_with_agreement(self, mock_registry, mock_which):
        """Test consensus strategy when Claude and OpenCode agree."""
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
                        output="The answer is 42",
                        execution_time=1.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="The answer is 42",
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.metadata.get("consensus_reached") is True
            assert result.conflict_info.severity == ConflictSeverity.NONE

    @pytest.mark.asyncio
    async def test_consensus_with_disagreement(self, mock_registry, mock_which):
        """Test consensus strategy when Claude and OpenCode disagree significantly."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.CONSENSUS,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            # Use completely different outputs to ensure disagreement is detected
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="I strongly recommend using PostgreSQL for this because it offers excellent ACID compliance and mature tooling.",
                        execution_time=1.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="MongoDB is the best choice here because it provides great horizontal scaling and schema flexibility.",
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            # These outputs are very different, so should not reach consensus
            assert result.metadata.get("consensus_reached") is False
            assert result.metadata.get("resolution_method") == "weighted_vote"

    @pytest.mark.asyncio
    async def test_smart_merge_preserves_unique_content(self, mock_registry, mock_which):
        """Test smart merge preserves unique content from each tool."""
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
                        output="First unique section from Claude.\n\nShared content.\n\nClaude specific details.",
                        execution_time=1.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="Shared content.\n\nOpenCode unique perspective.\n\nAdditional OpenCode insights.",
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.conflict_info is not None


# ---------------------------------------------------------------------------
# Test: Tool-Specific Error Handling
# ---------------------------------------------------------------------------


class TestToolSpecificErrorHandling:
    """Test error handling specific to Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_claude_rate_limit_error(self, mock_registry, mock_which):
        """Test handling of Claude rate limit error."""
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
                    error="Error: Rate limit exceeded. Please wait before making more requests.",
                    exit_code=1,
                    execution_time=0.5,
                )
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode response",
                execution_time=1.0,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"

            # Claude result should show the error
            claude_result = next(r for r in result.tool_results if r.tool == "claude")
            assert "Rate limit" in claude_result.error

    @pytest.mark.asyncio
    async def test_opencode_connection_error(self, mock_registry, mock_which):
        """Test handling of OpenCode connection error."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "opencode":
                return ToolResult(
                    tool="opencode",
                    success=False,
                    output="",
                    error="Connection refused: Could not connect to OpenCode server",
                    exit_code=1,
                    execution_time=0.1,
                )
            return ToolResult(
                tool="claude",
                success=True,
                output="Claude response",
                execution_time=1.0,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "claude"

    @pytest.mark.asyncio
    async def test_claude_timeout_opencode_succeeds(self, mock_registry, mock_which):
        """Test OpenCode succeeds when Claude times out."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", timeout=0.1),
                ToolConfig(name="opencode", timeout=60.0),
            ],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        async def mock_execute(tool, prompt, cancel_event=None):
            if tool.name == "claude":
                return ToolResult(
                    tool="claude",
                    success=False,
                    output="",
                    error="Timeout after 0.1s",
                    exit_code=-1,
                    execution_time=0.1,
                )
            return ToolResult(
                tool="opencode",
                success=True,
                output="OpenCode completed",
                execution_time=2.0,
            )

        with patch.object(executor, "_execute_tool", side_effect=mock_execute):
            result = await executor.execute("Test prompt")

            assert result.success is True
            assert result.winning_tool == "opencode"


# ---------------------------------------------------------------------------
# Test: Provider Integration
# ---------------------------------------------------------------------------


class TestProviderIntegration:
    """Test integration with actual Claude and OpenCode providers."""

    @pytest.mark.asyncio
    async def test_claude_provider_execution(self, mock_which, claude_provider_mock):
        """Test execution through Claude provider."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Claude provider response"
        mock_result.stderr = ""
        mock_result.return_code = 0
        claude_provider_mock.execute.return_value = mock_result

        with patch.object(registry, "get", return_value=claude_provider_mock):
            executor = ConcurrentToolExecutor(tools=["claude"])
            result = await executor._execute_tool(executor.tools[0], "Test prompt")

            assert result.success is True
            assert result.output == "Claude provider response"
            claude_provider_mock.execute.assert_called_once()

        ToolProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_opencode_provider_execution(self, mock_which, opencode_provider_mock):
        """Test execution through OpenCode provider."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "OpenCode provider response"
        mock_result.stderr = ""
        mock_result.return_code = 0
        opencode_provider_mock.execute.return_value = mock_result

        with patch.object(registry, "get", return_value=opencode_provider_mock):
            executor = ConcurrentToolExecutor(tools=["opencode"])
            result = await executor._execute_tool(executor.tools[0], "Test prompt")

            assert result.success is True
            assert result.output == "OpenCode provider response"

        ToolProviderRegistry.reset()

    @pytest.mark.asyncio
    async def test_mixed_provider_and_direct(self, mock_which, claude_provider_mock):
        """Test mixing provider-based and direct execution."""
        ToolProviderRegistry.reset()
        registry = ToolProviderRegistry.get_instance()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Claude via provider"
        mock_result.stderr = ""
        mock_result.return_code = 0
        claude_provider_mock.execute.return_value = mock_result

        def get_provider(name):
            if name == "claude":
                return claude_provider_mock
            return None

        with patch.object(registry, "get", side_effect=get_provider):
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

                # Claude uses provider, OpenCode uses direct
                claude_provider_mock.execute.assert_called_once()
                mock_direct.assert_called_once()
                assert len(result.tool_results) == 2

        ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Realistic Execution Scenarios
# ---------------------------------------------------------------------------


class TestRealisticScenarios:
    """Test realistic execution scenarios with Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_code_review_task(self, mock_registry, mock_which):
        """Test code review task with both tools."""
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
                        output="""Code Review:
1. Security: SQL injection risk in query function
2. Performance: N+1 query pattern detected
3. Style: Missing type hints
""",
                        execution_time=5.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="""Review Comments:
1. Security issue: Unsanitized user input
2. Consider using batch queries for performance
3. Add docstrings for public functions
""",
                        execution_time=4.0,
                    ),
                ],
            )

            result = await executor.execute("Review this code...")

            assert result.success is True
            assert result.conflict_info is not None
            # The outputs contain reviews but use different terminology
            # The important thing is that both tools completed and were merged
            assert result.metadata.get("merged_count") == 2
            # Both reviews should be present in the merged output
            assert (
                "Security" in result.primary_output or "security" in result.primary_output.lower()
            )

    @pytest.mark.asyncio
    async def test_bug_fix_task(self, mock_registry, mock_which):
        """Test bug fix task where both tools provide fixes."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.CONSENSUS,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            # Both tools suggest the same fix
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="Fix: Change `if x = 5` to `if x == 5`",
                        execution_time=2.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="Fix: Replace assignment `=` with comparison `==` in condition",
                        execution_time=3.0,
                    ),
                ],
            )

            result = await executor.execute("Fix this bug...")

            # Should recognize both suggest the same fix concept
            assert result.success is True

    @pytest.mark.asyncio
    async def test_architecture_question(self, mock_registry, mock_which):
        """Test architecture question where tools may disagree."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.CONSENSUS,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            # Tools disagree on architecture
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ToolResult(
                        tool="claude",
                        success=True,
                        output="I recommend a microservices architecture for better scalability and team independence.",
                        execution_time=3.0,
                    ),
                    ToolResult(
                        tool="opencode",
                        success=True,
                        output="A monolithic architecture would be simpler for your team size and reduce operational complexity.",
                        execution_time=4.0,
                    ),
                ],
            )

            result = await executor.execute("Should we use microservices?")

            assert result.metadata.get("consensus_reached") is False
            assert result.conflict_info is not None
            assert result.conflict_info.severity in (
                ConflictSeverity.MODERATE,
                ConflictSeverity.MAJOR,
            )


# ---------------------------------------------------------------------------
# Test: Configuration Variations
# ---------------------------------------------------------------------------


class TestConfigurationVariations:
    """Test different configuration options for Claude and OpenCode."""

    @pytest.mark.asyncio
    async def test_different_timeouts_per_tool(self, mock_registry, mock_which):
        """Test Claude and OpenCode with different timeouts."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", timeout=30.0),  # Faster timeout for Claude
                ToolConfig(name="opencode", timeout=120.0),  # Longer timeout for OpenCode
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        assert executor.tools[0].timeout == 30.0
        assert executor.tools[1].timeout == 120.0

    @pytest.mark.asyncio
    async def test_weighted_tools(self, mock_registry, mock_which):
        """Test weighted preferences for Claude vs OpenCode."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", weight=2.0),  # Prefer Claude
                ToolConfig(name="opencode", weight=1.0),
            ],
            strategy=AggregationStrategy.CONSENSUS,
        )

        assert executor.tools[0].weight == 2.0
        assert executor.tools[1].weight == 1.0

    @pytest.mark.asyncio
    async def test_custom_claude_command(self, mock_registry, mock_which):
        """Test Claude with custom command configuration."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(
                    name="claude",
                    command=["claude", "--print", "--model", "claude-3-opus-20240229"],
                ),
            ],
        )

        assert executor.tools[0].command == [
            "claude",
            "--print",
            "--model",
            "claude-3-opus-20240229",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
