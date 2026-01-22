"""Unit tests for ToolOrchestrator.

Tests cover:
- All execution strategies (round_robin, parallel, sequential, failover)
- Success and failure scenarios for each strategy
- Multi-tool coordination patterns
- Edge cases and error handling
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from aurora_cli.tool_providers.base import ToolProvider, ToolResult, ToolStatus
from aurora_cli.tool_providers.orchestrator import (
    ExecutionStrategy,
    OrchestratorResult,
    ToolOrchestrator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_console():
    """Create a mock console for output."""
    return MagicMock(spec=Console)


def create_mock_provider(name: str, success: bool = True, output: str = "output") -> ToolProvider:
    """Create a mock tool provider with configurable behavior."""
    provider = MagicMock(spec=ToolProvider)
    provider.name = name
    provider.display_name = name.capitalize()

    result = ToolResult(
        status=ToolStatus.SUCCESS if success else ToolStatus.FAILURE,
        stdout=output if success else "",
        stderr="" if success else "Error",
        return_code=0 if success else 1,
    )
    provider.execute.return_value = result
    return provider


def create_timeout_provider(name: str) -> ToolProvider:
    """Create a mock provider that times out."""
    provider = MagicMock(spec=ToolProvider)
    provider.name = name
    provider.display_name = name.capitalize()

    result = ToolResult(
        status=ToolStatus.TIMEOUT,
        stdout="",
        stderr="Timed out after 60s",
        return_code=-1,
    )
    provider.execute.return_value = result
    return provider


# ---------------------------------------------------------------------------
# Test: ToolOrchestrator Initialization
# ---------------------------------------------------------------------------


class TestOrchestratorInit:
    """Test ToolOrchestrator initialization."""

    def test_init_with_providers(self, mock_console):
        """Test initialization with providers."""
        providers = [create_mock_provider("claude"), create_mock_provider("opencode")]

        orchestrator = ToolOrchestrator(providers, console=mock_console)

        assert len(orchestrator.providers) == 2
        assert orchestrator.strategy == ExecutionStrategy.ROUND_ROBIN
        assert orchestrator.console == mock_console

    def test_init_with_strategy(self, mock_console):
        """Test initialization with custom strategy."""
        providers = [create_mock_provider("claude")]

        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        assert orchestrator.strategy == ExecutionStrategy.FAILOVER

    def test_init_empty_providers_raises(self, mock_console):
        """Test that empty providers list raises ValueError."""
        with pytest.raises(ValueError, match="At least one tool provider is required"):
            ToolOrchestrator([], console=mock_console)

    def test_init_default_console(self):
        """Test that default console is created if not provided."""
        providers = [create_mock_provider("claude")]

        orchestrator = ToolOrchestrator(providers)

        assert orchestrator.console is not None
        assert isinstance(orchestrator.console, Console)


# ---------------------------------------------------------------------------
# Test: Round-Robin Strategy
# ---------------------------------------------------------------------------


class TestRoundRobinStrategy:
    """Test round-robin execution strategy."""

    def test_round_robin_first_iteration(self, mock_console):
        """Test round-robin selects first provider on iteration 1."""
        providers = [
            create_mock_provider("claude", output="Claude output"),
            create_mock_provider("opencode", output="OpenCode output"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "claude"
        assert result.result.stdout == "Claude output"
        assert result.iteration == 1
        assert result.strategy == ExecutionStrategy.ROUND_ROBIN

    def test_round_robin_second_iteration(self, mock_console):
        """Test round-robin selects second provider on iteration 2."""
        providers = [
            create_mock_provider("claude"),
            create_mock_provider("opencode", output="OpenCode output"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=2)

        assert result.tool_name == "opencode"
        assert result.result.stdout == "OpenCode output"

    def test_round_robin_wraps_around(self, mock_console):
        """Test round-robin wraps back to first provider."""
        providers = [
            create_mock_provider("claude", output="Claude"),
            create_mock_provider("opencode", output="OpenCode"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        # Iteration 3 should wrap to first provider (index 0)
        result = orchestrator.execute("test context", iteration=3)

        assert result.tool_name == "claude"

    def test_round_robin_three_providers(self, mock_console):
        """Test round-robin with three providers."""
        providers = [
            create_mock_provider("claude"),
            create_mock_provider("opencode"),
            create_mock_provider("cursor"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        # Test sequence: 1->claude, 2->opencode, 3->cursor, 4->claude
        assert orchestrator.execute("ctx", iteration=1).tool_name == "claude"
        assert orchestrator.execute("ctx", iteration=2).tool_name == "opencode"
        assert orchestrator.execute("ctx", iteration=3).tool_name == "cursor"
        assert orchestrator.execute("ctx", iteration=4).tool_name == "claude"

    def test_round_robin_failure_still_returns(self, mock_console):
        """Test round-robin returns result even on failure."""
        providers = [
            create_mock_provider("claude", success=False),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "claude"
        assert result.result.success is False


# ---------------------------------------------------------------------------
# Test: Parallel Strategy
# ---------------------------------------------------------------------------


class TestParallelStrategy:
    """Test parallel execution strategy."""

    def test_parallel_first_success(self, mock_console):
        """Test parallel returns first successful result."""
        providers = [
            create_mock_provider("claude", output="Claude success"),
            create_mock_provider("opencode", output="OpenCode success"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.PARALLEL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "claude"
        assert result.result.success is True
        assert result.result.stdout == "Claude success"

    def test_parallel_skip_failure_use_success(self, mock_console):
        """Test parallel skips failed tools, uses successful one."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", output="OpenCode success"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.PARALLEL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "opencode"
        assert result.result.success is True

    def test_parallel_all_fail_returns_last(self, mock_console):
        """Test parallel returns last result when all fail."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", success=False),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.PARALLEL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "opencode"
        assert result.result.success is False

    def test_parallel_collects_all_results(self, mock_console):
        """Test parallel collects results from all tools."""
        providers = [
            create_mock_provider("claude", output="Claude output"),
            create_mock_provider("opencode", output="OpenCode output"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.PARALLEL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        # Should stop at first success, but still record that result
        assert "claude" in result.all_results
        # First success stops execution, so opencode may not be in results

    def test_parallel_single_provider(self, mock_console):
        """Test parallel with single provider."""
        providers = [create_mock_provider("claude", output="Only one")]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.PARALLEL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "claude"
        assert result.result.stdout == "Only one"


# ---------------------------------------------------------------------------
# Test: Sequential Strategy
# ---------------------------------------------------------------------------


class TestSequentialStrategy:
    """Test sequential execution strategy."""

    def test_sequential_first_success(self, mock_console):
        """Test sequential returns on first success."""
        providers = [
            create_mock_provider("claude", output="Claude success"),
            create_mock_provider("opencode", output="OpenCode success"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.SEQUENTIAL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "claude"
        assert result.result.success is True
        # Only first provider should have been executed
        assert len(result.all_results) == 1

    def test_sequential_skip_to_second(self, mock_console):
        """Test sequential tries second after first fails."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", output="OpenCode success"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.SEQUENTIAL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "opencode"
        assert result.result.success is True
        assert len(result.all_results) == 2

    def test_sequential_all_fail(self, mock_console):
        """Test sequential returns last when all fail."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", success=False),
            create_mock_provider("cursor", success=False),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.SEQUENTIAL,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "cursor"
        assert result.result.success is False
        assert len(result.all_results) == 3


# ---------------------------------------------------------------------------
# Test: Failover Strategy
# ---------------------------------------------------------------------------


class TestFailoverStrategy:
    """Test failover execution strategy."""

    def test_failover_primary_success(self, mock_console):
        """Test failover uses primary on success."""
        providers = [
            create_mock_provider("claude", output="Primary success"),
            create_mock_provider("opencode", output="Backup"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "claude"
        assert result.result.success is True
        # Only primary should have been called
        assert len(result.all_results) == 1

    def test_failover_to_secondary(self, mock_console):
        """Test failover to secondary on primary failure."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", output="Failover success"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "opencode"
        assert result.result.success is True
        assert len(result.all_results) == 2

    def test_failover_on_timeout(self, mock_console):
        """Test failover triggers on timeout."""
        providers = [
            create_timeout_provider("claude"),
            create_mock_provider("opencode", output="Backup success"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "opencode"
        assert result.result.success is True

    def test_failover_chain(self, mock_console):
        """Test failover through multiple backups."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", success=False),
            create_mock_provider("cursor", output="Third time's the charm"),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "cursor"
        assert result.result.success is True
        assert len(result.all_results) == 3

    def test_failover_all_exhausted(self, mock_console):
        """Test failover when all tools fail."""
        providers = [
            create_mock_provider("claude", success=False),
            create_mock_provider("opencode", success=False),
        ]
        orchestrator = ToolOrchestrator(
            providers,
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        result = orchestrator.execute("test context", iteration=1)

        assert result.tool_name == "opencode"
        assert result.result.success is False
        assert len(result.all_results) == 2


# ---------------------------------------------------------------------------
# Test: OrchestratorResult
# ---------------------------------------------------------------------------


class TestOrchestratorResult:
    """Test OrchestratorResult dataclass."""

    def test_result_fields(self):
        """Test OrchestratorResult has correct fields."""
        tool_result = ToolResult(
            status=ToolStatus.SUCCESS,
            stdout="output",
            stderr="",
            return_code=0,
        )

        result = OrchestratorResult(
            tool_name="claude",
            result=tool_result,
            iteration=5,
            strategy=ExecutionStrategy.ROUND_ROBIN,
            all_results={"claude": tool_result},
        )

        assert result.tool_name == "claude"
        assert result.result == tool_result
        assert result.iteration == 5
        assert result.strategy == ExecutionStrategy.ROUND_ROBIN
        assert "claude" in result.all_results

    def test_result_default_all_results(self):
        """Test OrchestratorResult defaults all_results to empty dict."""
        tool_result = ToolResult(
            status=ToolStatus.SUCCESS,
            stdout="",
            stderr="",
            return_code=0,
        )

        result = OrchestratorResult(
            tool_name="claude",
            result=tool_result,
            iteration=1,
            strategy=ExecutionStrategy.SEQUENTIAL,
        )

        assert result.all_results == {}


# ---------------------------------------------------------------------------
# Test: ExecutionStrategy Enum
# ---------------------------------------------------------------------------


class TestExecutionStrategy:
    """Test ExecutionStrategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert ExecutionStrategy.ROUND_ROBIN.value == "round_robin"
        assert ExecutionStrategy.PARALLEL.value == "parallel"
        assert ExecutionStrategy.SEQUENTIAL.value == "sequential"
        assert ExecutionStrategy.FAILOVER.value == "failover"

    def test_strategy_from_string(self):
        """Test creating strategy from string value."""
        assert ExecutionStrategy("round_robin") == ExecutionStrategy.ROUND_ROBIN
        assert ExecutionStrategy("parallel") == ExecutionStrategy.PARALLEL


# ---------------------------------------------------------------------------
# Test: Working Directory and Timeout
# ---------------------------------------------------------------------------


class TestExecutionParameters:
    """Test execution parameters are passed correctly."""

    def test_working_dir_passed(self, mock_console):
        """Test working directory is passed to provider."""
        provider = create_mock_provider("claude")
        orchestrator = ToolOrchestrator(
            [provider],
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )
        working_dir = Path("/tmp/test")

        orchestrator.execute("context", iteration=1, working_dir=working_dir)

        provider.execute.assert_called_once_with("context", working_dir, 600)

    def test_timeout_passed(self, mock_console):
        """Test timeout is passed to provider."""
        provider = create_mock_provider("claude")
        orchestrator = ToolOrchestrator(
            [provider],
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        orchestrator.execute("context", iteration=1, timeout=300)

        provider.execute.assert_called_once_with("context", None, 300)


# ---------------------------------------------------------------------------
# Test: Error Handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error handling in orchestrator."""

    def test_unknown_strategy_raises(self, mock_console):
        """Test that unknown strategy raises ValueError."""
        providers = [create_mock_provider("claude")]
        orchestrator = ToolOrchestrator(providers, console=mock_console)

        # Manually set invalid strategy
        orchestrator.strategy = "invalid"

        with pytest.raises(ValueError, match="Unknown strategy"):
            orchestrator.execute("context", iteration=1)


# ---------------------------------------------------------------------------
# Test: Multi-Tool Integration Scenarios
# ---------------------------------------------------------------------------


class TestMultiToolScenarios:
    """Test realistic multi-tool scenarios."""

    def test_claude_opencode_failover(self, mock_console):
        """Test Claude to OpenCode failover scenario."""
        claude = create_mock_provider("claude", success=False)
        opencode = create_mock_provider("opencode", output="OpenCode handled it")

        orchestrator = ToolOrchestrator(
            [claude, opencode],
            strategy=ExecutionStrategy.FAILOVER,
            console=mock_console,
        )

        result = orchestrator.execute("Fix the bug", iteration=1)

        assert result.tool_name == "opencode"
        assert "OpenCode handled it" in result.result.stdout

    def test_code_review_round_robin(self, mock_console):
        """Test code review with multiple tools in round-robin."""
        claude = create_mock_provider("claude", output="Claude review")
        opencode = create_mock_provider("opencode", output="OpenCode review")

        orchestrator = ToolOrchestrator(
            [claude, opencode],
            strategy=ExecutionStrategy.ROUND_ROBIN,
            console=mock_console,
        )

        # Simulate multiple review iterations
        results = [orchestrator.execute("Review code", iteration=i) for i in range(1, 5)]

        # Should alternate between tools
        assert results[0].tool_name == "claude"
        assert results[1].tool_name == "opencode"
        assert results[2].tool_name == "claude"
        assert results[3].tool_name == "opencode"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
