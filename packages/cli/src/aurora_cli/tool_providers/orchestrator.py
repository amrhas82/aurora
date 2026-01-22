"""Multi-tool orchestration for headless execution."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from rich.console import Console

from aurora_cli.tool_providers.base import ToolProvider, ToolResult, ToolStatus


class ExecutionStrategy(Enum):
    """Strategy for executing multiple tools."""

    ROUND_ROBIN = "round_robin"  # Alternate between tools each iteration
    PARALLEL = "parallel"  # Run all tools on same context (first success wins)
    SEQUENTIAL = "sequential"  # Run tools in sequence, stop on first success
    FAILOVER = "failover"  # Try first tool, failover to next on failure


@dataclass
class OrchestratorResult:
    """Result of an orchestrated multi-tool execution."""

    tool_name: str
    result: ToolResult
    iteration: int
    strategy: ExecutionStrategy
    all_results: dict[str, ToolResult] = field(default_factory=dict)


class ToolOrchestrator:
    """Orchestrates execution across multiple AI tools.

    Supports different execution strategies:
    - round_robin: Alternate between tools each iteration
    - parallel: Run all tools, use first success
    - sequential: Run tools in order until success
    - failover: Primary tool with automatic failover
    """

    def __init__(
        self,
        providers: list[ToolProvider],
        strategy: ExecutionStrategy = ExecutionStrategy.ROUND_ROBIN,
        console: Console | None = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            providers: List of tool providers to orchestrate
            strategy: Execution strategy to use
            console: Rich console for output (optional)

        """
        if not providers:
            raise ValueError("At least one tool provider is required")

        self.providers = providers
        self.strategy = strategy
        self.console = console or Console()
        self._current_index = 0

    def execute(
        self,
        context: str,
        iteration: int,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> OrchestratorResult:
        """Execute tools according to the configured strategy.

        Args:
            context: The prompt/context to pass to tools
            iteration: Current iteration number (for round-robin)
            working_dir: Working directory for execution
            timeout: Maximum execution time per tool

        Returns:
            OrchestratorResult with execution details

        """
        if self.strategy == ExecutionStrategy.ROUND_ROBIN:
            return self._execute_round_robin(context, iteration, working_dir, timeout)
        if self.strategy == ExecutionStrategy.PARALLEL:
            return self._execute_parallel(context, iteration, working_dir, timeout)
        if self.strategy == ExecutionStrategy.SEQUENTIAL:
            return self._execute_sequential(context, iteration, working_dir, timeout)
        if self.strategy == ExecutionStrategy.FAILOVER:
            return self._execute_failover(context, iteration, working_dir, timeout)
        raise ValueError(f"Unknown strategy: {self.strategy}")

    def _execute_round_robin(
        self,
        context: str,
        iteration: int,
        working_dir: Path | None,
        timeout: int,
    ) -> OrchestratorResult:
        """Execute tools in round-robin fashion."""
        provider_index = (iteration - 1) % len(self.providers)
        provider = self.providers[provider_index]

        self.console.print(f"[dim]Using {provider.display_name} (round-robin)[/]")
        result = provider.execute(context, working_dir, timeout)

        return OrchestratorResult(
            tool_name=provider.name,
            result=result,
            iteration=iteration,
            strategy=self.strategy,
            all_results={provider.name: result},
        )

    def _execute_parallel(
        self,
        context: str,
        iteration: int,
        working_dir: Path | None,
        timeout: int,
    ) -> OrchestratorResult:
        """Execute all tools in parallel, return first success.

        Note: Currently sequential due to subprocess limitations.
        Could use ThreadPoolExecutor for true parallelism.
        """
        all_results: dict[str, ToolResult] = {}

        for provider in self.providers:
            self.console.print(f"[dim]Trying {provider.display_name}...[/]")
            result = provider.execute(context, working_dir, timeout)
            all_results[provider.name] = result

            if result.success:
                self.console.print(f"[green]Success with {provider.display_name}[/]")
                return OrchestratorResult(
                    tool_name=provider.name,
                    result=result,
                    iteration=iteration,
                    strategy=self.strategy,
                    all_results=all_results,
                )

        # No success, return last result
        last_provider = self.providers[-1]
        return OrchestratorResult(
            tool_name=last_provider.name,
            result=all_results[last_provider.name],
            iteration=iteration,
            strategy=self.strategy,
            all_results=all_results,
        )

    def _execute_sequential(
        self,
        context: str,
        iteration: int,
        working_dir: Path | None,
        timeout: int,
    ) -> OrchestratorResult:
        """Execute tools sequentially until first success."""
        all_results: dict[str, ToolResult] = {}

        for provider in self.providers:
            self.console.print(f"[dim]Running {provider.display_name}...[/]")
            result = provider.execute(context, working_dir, timeout)
            all_results[provider.name] = result

            if result.success:
                return OrchestratorResult(
                    tool_name=provider.name,
                    result=result,
                    iteration=iteration,
                    strategy=self.strategy,
                    all_results=all_results,
                )

        # All failed, return last result
        last_provider = self.providers[-1]
        return OrchestratorResult(
            tool_name=last_provider.name,
            result=all_results[last_provider.name],
            iteration=iteration,
            strategy=self.strategy,
            all_results=all_results,
        )

    def _execute_failover(
        self,
        context: str,
        iteration: int,
        working_dir: Path | None,
        timeout: int,
    ) -> OrchestratorResult:
        """Execute primary tool with failover to secondaries."""
        all_results: dict[str, ToolResult] = {}
        primary = self.providers[0]

        self.console.print(f"[dim]Running primary: {primary.display_name}[/]")
        result = primary.execute(context, working_dir, timeout)
        all_results[primary.name] = result

        if result.success:
            return OrchestratorResult(
                tool_name=primary.name,
                result=result,
                iteration=iteration,
                strategy=self.strategy,
                all_results=all_results,
            )

        # Primary failed, try failovers
        if result.status == ToolStatus.TIMEOUT:
            self.console.print(f"[yellow]{primary.display_name} timed out, trying failover...[/]")
        else:
            self.console.print(f"[yellow]{primary.display_name} failed, trying failover...[/]")

        for provider in self.providers[1:]:
            self.console.print(f"[dim]Failover to {provider.display_name}[/]")
            result = provider.execute(context, working_dir, timeout)
            all_results[provider.name] = result

            if result.success:
                self.console.print(f"[green]Failover successful with {provider.display_name}[/]")
                return OrchestratorResult(
                    tool_name=provider.name,
                    result=result,
                    iteration=iteration,
                    strategy=self.strategy,
                    all_results=all_results,
                )

        # All failovers exhausted
        last_provider = self.providers[-1]
        self.console.print("[red]All failovers exhausted[/]")
        return OrchestratorResult(
            tool_name=last_provider.name,
            result=all_results[last_provider.name],
            iteration=iteration,
            strategy=self.strategy,
            all_results=all_results,
        )
