"""Integration tests for multi-tool orchestration scenarios.

Tests cover end-to-end multi-tool execution patterns combining:
- ConcurrentToolExecutor for async parallel execution
- ToolOrchestrator for synchronous strategy-based execution
- ToolProviderRegistry for dynamic tool discovery
- Headless command integration with both execution paths
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from aurora_cli.commands.headless import headless_command
from aurora_cli.concurrent_executor import (
    AggregatedResult,
    AggregationStrategy,
    ConcurrentToolExecutor,
    ToolConfig,
)
from aurora_cli.concurrent_executor import ToolResult as ConcurrentToolResult
from aurora_cli.tool_providers import ClaudeToolProvider, OpenCodeToolProvider, ToolProviderRegistry
from aurora_cli.tool_providers.base import ToolResult, ToolStatus
from aurora_cli.tool_providers.orchestrator import ExecutionStrategy, ToolOrchestrator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_headless_workspace(tmp_path):
    """Create a complete headless workspace."""
    headless_dir = tmp_path / ".aurora" / "headless"
    headless_dir.mkdir(parents=True)

    prompt = headless_dir / "prompt.md"
    prompt.write_text(
        """# Goal
Complete the multi-tool integration test.

# Success Criteria
- [ ] Both Claude and OpenCode execute successfully
- [ ] Results are properly aggregated
"""
    )

    scratchpad = headless_dir / "scratchpad.md"
    scratchpad.write_text(
        """# Scratchpad
STATUS: IN_PROGRESS

## Progress
Starting multi-tool execution...
"""
    )

    return {
        "root": tmp_path,
        "headless_dir": headless_dir,
        "prompt": prompt,
        "scratchpad": scratchpad,
    }


@pytest.fixture
def mock_tools_available():
    """Mock both Claude and OpenCode as available in PATH."""
    with patch("shutil.which") as mock:
        mock.side_effect = lambda x: (
            f"/usr/bin/{x}" if x in ("claude", "opencode", "cursor") else None
        )
        yield mock


@pytest.fixture
def mock_git_branch():
    """Mock git to return a feature branch."""
    with patch("subprocess.run") as mock:
        result = Mock()
        result.returncode = 0
        result.stdout = "feature-multi-tool\n"
        result.stderr = ""
        mock.return_value = result
        yield mock


@pytest.fixture
def reset_registry():
    """Reset ToolProviderRegistry between tests."""
    ToolProviderRegistry.reset()
    yield
    ToolProviderRegistry.reset()


# ---------------------------------------------------------------------------
# Test: Orchestrator + Registry Integration
# ---------------------------------------------------------------------------


class TestOrchestratorRegistryIntegration:
    """Test ToolOrchestrator with ToolProviderRegistry."""

    def test_orchestrator_with_registry_providers(self, reset_registry, mock_tools_available):
        """Test orchestrator using providers from registry."""
        registry = ToolProviderRegistry.get_instance()

        with patch.object(ClaudeToolProvider, "execute") as mock_claude_exec:
            with patch.object(OpenCodeToolProvider, "execute") as mock_opencode_exec:
                mock_claude_exec.return_value = ToolResult(
                    status=ToolStatus.SUCCESS,
                    stdout="Claude from registry",
                    stderr="",
                    return_code=0,
                )
                mock_opencode_exec.return_value = ToolResult(
                    status=ToolStatus.SUCCESS,
                    stdout="OpenCode from registry",
                    stderr="",
                    return_code=0,
                )

                providers = registry.get_multiple(["claude", "opencode"])
                orchestrator = ToolOrchestrator(
                    providers,
                    strategy=ExecutionStrategy.ROUND_ROBIN,
                )

                result1 = orchestrator.execute("Test", iteration=1)
                result2 = orchestrator.execute("Test", iteration=2)

                assert result1.tool_name == "claude"
                assert result2.tool_name == "opencode"

    def test_orchestrator_failover_with_registry(self, reset_registry, mock_tools_available):
        """Test failover using registry providers."""
        registry = ToolProviderRegistry.get_instance()

        with patch.object(ClaudeToolProvider, "execute") as mock_claude:
            with patch.object(OpenCodeToolProvider, "execute") as mock_opencode:
                # Claude fails
                mock_claude.return_value = ToolResult(
                    status=ToolStatus.FAILURE,
                    stdout="",
                    stderr="Claude unavailable",
                    return_code=1,
                )
                # OpenCode succeeds
                mock_opencode.return_value = ToolResult(
                    status=ToolStatus.SUCCESS,
                    stdout="OpenCode backup",
                    stderr="",
                    return_code=0,
                )

                providers = registry.get_multiple(["claude", "opencode"])
                orchestrator = ToolOrchestrator(
                    providers,
                    strategy=ExecutionStrategy.FAILOVER,
                )

                result = orchestrator.execute("Test", iteration=1)

                assert result.tool_name == "opencode"
                assert result.result.success is True


# ---------------------------------------------------------------------------
# Test: ConcurrentToolExecutor + Orchestrator Comparison
# ---------------------------------------------------------------------------


class TestExecutorOrchestratorComparison:
    """Compare behavior between ConcurrentToolExecutor and ToolOrchestrator."""

    @pytest.mark.asyncio
    async def test_first_success_equivalence(self, reset_registry, mock_tools_available):
        """Test that first_success strategy behaves similarly in both."""
        # ConcurrentToolExecutor (async)
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.FIRST_SUCCESS,
        )

        # Mock both tools
        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mock_execute(tool, prompt, cancel_event=None):
                return ConcurrentToolResult(
                    tool=tool.name,
                    success=True,
                    output=f"{tool.name} async output",
                    execution_time=0.1,
                )

            mock_exec.side_effect = mock_execute

            async_result = await executor.execute("Test prompt")

            assert async_result.success is True
            assert async_result.winning_tool in ["claude", "opencode"]

    def test_sequential_equivalence(self, reset_registry, mock_tools_available):
        """Test sequential strategy in orchestrator."""
        registry = ToolProviderRegistry.get_instance()

        with patch.object(ClaudeToolProvider, "execute") as mock_claude:
            with patch.object(OpenCodeToolProvider, "execute") as mock_opencode:
                # First fails, second succeeds
                mock_claude.return_value = ToolResult(
                    status=ToolStatus.FAILURE, stdout="", stderr="Error", return_code=1
                )
                mock_opencode.return_value = ToolResult(
                    status=ToolStatus.SUCCESS, stdout="Success", stderr="", return_code=0
                )

                providers = registry.get_multiple(["claude", "opencode"])
                orchestrator = ToolOrchestrator(providers, strategy=ExecutionStrategy.SEQUENTIAL)

                result = orchestrator.execute("Test", iteration=1)

                # Sequential should try claude first, then opencode
                assert result.tool_name == "opencode"
                mock_claude.assert_called_once()
                mock_opencode.assert_called_once()


# ---------------------------------------------------------------------------
# Test: CLI Integration with Multi-Tool
# ---------------------------------------------------------------------------


class TestCLIMultiToolIntegration:
    """Test CLI integration with multi-tool execution."""

    def test_cli_two_tools_parallel_mode(
        self, runner, temp_headless_workspace, mock_tools_available, mock_git_branch
    ):
        """Test CLI invocation with two tools in parallel mode."""
        with patch("pathlib.Path.cwd", return_value=temp_headless_workspace["root"]):
            with patch("aurora_cli.commands.headless.asyncio.run") as mock_asyncio:
                mock_asyncio.return_value = None

                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_headless_workspace["prompt"]),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--max",
                        "1",
                        "--strategy",
                        "first_success",
                    ],
                )

                # Should invoke async execution for parallel
                mock_asyncio.assert_called_once()
                assert "parallel" in result.output or "claude, opencode" in result.output

    def test_cli_two_tools_sequential_mode(
        self, runner, temp_headless_workspace, mock_tools_available, mock_git_branch
    ):
        """Test CLI invocation with two tools in sequential mode."""
        with patch("pathlib.Path.cwd", return_value=temp_headless_workspace["root"]):
            with patch("aurora_cli.commands.headless._run_single_tool_loop") as mock_single:
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_headless_workspace["prompt"]),
                        "-t",
                        "claude",
                        "-t",
                        "opencode",
                        "--sequential",
                        "--max",
                        "1",
                    ],
                )

                mock_single.assert_called_once()
                call_kwargs = mock_single.call_args[1]
                assert call_kwargs["sequential_multi"] is True

    def test_cli_strategy_selection(self, runner, temp_headless_workspace, mock_tools_available):
        """Test different aggregation strategies via CLI."""
        strategies = ["first_success", "all_complete", "voting", "best_score", "merge"]

        with patch("pathlib.Path.cwd", return_value=temp_headless_workspace["root"]):
            for strategy in strategies:
                result = runner.invoke(
                    headless_command,
                    [
                        "-p",
                        str(temp_headless_workspace["prompt"]),
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


# ---------------------------------------------------------------------------
# Test: Real-World Workflow Scenarios
# ---------------------------------------------------------------------------


class TestRealWorldWorkflows:
    """Test real-world multi-tool workflow scenarios."""

    @pytest.mark.asyncio
    async def test_code_review_parallel(self, reset_registry, mock_tools_available):
        """Test parallel code review from Claude and OpenCode."""
        executor = ConcurrentToolExecutor(
            tools=[
                ToolConfig(name="claude", weight=2.0),  # Claude has higher weight
                ToolConfig(name="opencode", weight=1.0),
            ],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mock_execute(tool, prompt, cancel_event=None):
                if tool.name == "claude":
                    return ConcurrentToolResult(
                        tool="claude",
                        success=True,
                        output="Claude found: unused variable on line 42",
                        execution_time=2.0,
                    )
                else:
                    return ConcurrentToolResult(
                        tool="opencode",
                        success=True,
                        output="OpenCode found: missing error handling",
                        execution_time=1.5,
                    )

            mock_exec.side_effect = mock_execute

            result = await executor.execute("Review this code for issues")

            assert result.success is True
            assert len(result.tool_results) == 2

            # Both tools should have contributed
            claude_result = next(r for r in result.tool_results if r.tool == "claude")
            opencode_result = next(r for r in result.tool_results if r.tool == "opencode")
            assert "line 42" in claude_result.output
            assert "error handling" in opencode_result.output

    @pytest.mark.asyncio
    async def test_bug_fix_with_voting(self, reset_registry, mock_tools_available):
        """Test bug fix scenario with voting strategy."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode", "cursor"],
            strategy=AggregationStrategy.VOTING,
        )

        with patch.object(executor, "_execute_all_complete") as mock_all:
            # 2 tools agree, 1 disagrees
            mock_all.return_value = AggregatedResult(
                success=True,
                primary_output="",
                strategy_used=AggregationStrategy.ALL_COMPLETE,
                tool_results=[
                    ConcurrentToolResult(
                        tool="claude",
                        success=True,
                        output="Fix: add null check",
                        execution_time=1.0,
                    ),
                    ConcurrentToolResult(
                        tool="opencode",
                        success=True,
                        output="Fix: add null check",
                        execution_time=1.0,
                    ),
                    ConcurrentToolResult(
                        tool="cursor",
                        success=True,
                        output="Fix: use optional chaining",
                        execution_time=1.0,
                    ),
                ],
            )

            result = await executor.execute("Fix NullPointerException")

            assert result.success is True
            # The majority vote should win
            assert "null check" in result.primary_output.lower() or result.winning_tool in [
                "claude",
                "opencode",
            ]

    def test_iterative_development_round_robin(self, reset_registry, mock_tools_available):
        """Test iterative development with round-robin tool selection."""
        registry = ToolProviderRegistry.get_instance()

        execution_log = []

        def mock_claude_execute(context, working_dir=None, timeout=600):
            execution_log.append(("claude", context[:20]))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                stdout="Claude: implemented feature",
                stderr="",
                return_code=0,
            )

        def mock_opencode_execute(context, working_dir=None, timeout=600):
            execution_log.append(("opencode", context[:20]))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                stdout="OpenCode: added tests",
                stderr="",
                return_code=0,
            )

        with patch.object(ClaudeToolProvider, "execute", mock_claude_execute):
            with patch.object(OpenCodeToolProvider, "execute", mock_opencode_execute):
                providers = registry.get_multiple(["claude", "opencode"])
                orchestrator = ToolOrchestrator(providers, strategy=ExecutionStrategy.ROUND_ROBIN)

                # Simulate 4 development iterations
                for i in range(1, 5):
                    orchestrator.execute(f"Iteration {i}: continue development", iteration=i)

                # Verify round-robin alternation
                assert execution_log[0][0] == "claude"
                assert execution_log[1][0] == "opencode"
                assert execution_log[2][0] == "claude"
                assert execution_log[3][0] == "opencode"


# ---------------------------------------------------------------------------
# Test: Error Recovery Scenarios
# ---------------------------------------------------------------------------


class TestErrorRecoveryScenarios:
    """Test error recovery in multi-tool scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self, reset_registry, mock_tools_available):
        """Test recovery when one tool fails but others succeed."""
        executor = ConcurrentToolExecutor(
            tools=["claude", "opencode"],
            strategy=AggregationStrategy.ALL_COMPLETE,
        )

        with patch.object(executor, "_execute_tool") as mock_exec:

            async def mock_execute(tool, prompt, cancel_event=None):
                if tool.name == "claude":
                    return ConcurrentToolResult(
                        tool="claude",
                        success=False,
                        output="",
                        error="Connection timeout",
                        execution_time=30.0,
                    )
                return ConcurrentToolResult(
                    tool="opencode",
                    success=True,
                    output="OpenCode completed successfully",
                    execution_time=2.0,
                )

            mock_exec.side_effect = mock_execute

            result = await executor.execute("Complete the task")

            # Should succeed with partial results
            assert result.success is True
            assert result.winning_tool == "opencode"

            # Failed tool should be recorded
            claude_result = next(r for r in result.tool_results if r.tool == "claude")
            assert claude_result.success is False
            assert "timeout" in claude_result.error.lower()

    def test_failover_chain_exhaustion(self, reset_registry, mock_tools_available):
        """Test complete failover chain when all tools fail."""
        registry = ToolProviderRegistry.get_instance()

        def make_failing_execute(tool_name):
            def execute(context, working_dir=None, timeout=600):
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    stdout="",
                    stderr=f"{tool_name} failed",
                    return_code=1,
                )

            return execute

        with patch.object(ClaudeToolProvider, "execute", make_failing_execute("Claude")):
            with patch.object(OpenCodeToolProvider, "execute", make_failing_execute("OpenCode")):
                providers = registry.get_multiple(["claude", "opencode"])
                orchestrator = ToolOrchestrator(providers, strategy=ExecutionStrategy.FAILOVER)

                result = orchestrator.execute("Impossible task", iteration=1)

                assert result.result.success is False
                assert len(result.all_results) == 2
                assert all(not r.success for r in result.all_results.values())


# ---------------------------------------------------------------------------
# Test: Scratchpad State Management
# ---------------------------------------------------------------------------


class TestScratchpadStateManagement:
    """Test scratchpad state management with multi-tool execution."""

    @pytest.mark.asyncio
    async def test_scratchpad_updates_across_tools(self, temp_headless_workspace):
        """Test that scratchpad updates are visible to subsequent tool calls."""
        scratchpad = temp_headless_workspace["scratchpad"]

        with patch("aurora_cli.concurrent_executor.ConcurrentToolExecutor") as MockExecutor:
            mock_executor = MagicMock()
            MockExecutor.return_value = mock_executor

            iteration_contexts = []

            async def mock_execute(context):
                iteration_contexts.append(context)
                # Simulate tool updating scratchpad
                current = scratchpad.read_text()
                scratchpad.write_text(
                    current + f"\n\n## Tool Update {len(iteration_contexts)}\nProgress made..."
                )

                if len(iteration_contexts) >= 2:
                    scratchpad.write_text(scratchpad.read_text() + "\n\nSTATUS: DONE")

                return AggregatedResult(
                    success=True,
                    primary_output="Progress",
                    strategy_used=AggregationStrategy.FIRST_SUCCESS,
                    tool_results=[],
                )

            mock_executor.execute = mock_execute

            from aurora_cli.commands.headless import _run_multi_tool_loop

            await _run_multi_tool_loop(
                tools_list=["claude", "opencode"],
                prompt="Test prompt",
                scratchpad=scratchpad,
                max_iter=10,
                test_cmd=None,
                strategy="first_success",
            )

            # Verify iterations saw updated scratchpad
            assert len(iteration_contexts) == 2
            # Second iteration should see updates from first
            if len(iteration_contexts) > 1:
                assert "Tool Update 1" in iteration_contexts[1]


# ---------------------------------------------------------------------------
# Test: Configuration Integration
# ---------------------------------------------------------------------------


class TestConfigurationIntegration:
    """Test configuration integration with multi-tool execution."""

    def test_tool_configs_from_config(self, runner, temp_headless_workspace, mock_tools_available):
        """Test that tool configurations from config are applied."""
        with patch("pathlib.Path.cwd", return_value=temp_headless_workspace["root"]):
            with patch("aurora_cli.commands.headless.load_config") as mock_config:
                mock_cfg = MagicMock()
                mock_cfg.headless_tools = ["claude", "opencode"]
                mock_cfg.headless_max_iterations = 5
                mock_cfg.headless_strategy = "all_complete"
                mock_cfg.headless_parallel = True
                mock_cfg.headless_timeout = 300
                mock_cfg.headless_tool_configs = {
                    "claude": {"timeout": 120, "priority": 1},
                    "opencode": {"timeout": 180, "priority": 2},
                }
                mock_cfg.headless_routing_rules = []
                mock_config.return_value = mock_cfg

                result = runner.invoke(
                    headless_command,
                    ["-p", str(temp_headless_workspace["prompt"]), "--show-config"],
                )

                assert result.exit_code == 0
                assert "claude" in result.output
                assert "opencode" in result.output
                assert "all_complete" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
