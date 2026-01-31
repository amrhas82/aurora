"""Concurrent tool executor for multi-tool parallel execution.

Enables running the same prompt across multiple AI tools (Claude, OpenCode, etc.)
simultaneously with configurable result aggregation strategies.

Uses the ToolProviderRegistry for dynamic tool instantiation and proper
command building per tool type.

Example usage:
    # Run same prompt with Claude and OpenCode in parallel
    executor = ConcurrentToolExecutor(
        tools=["claude", "opencode"],
        strategy=AggregationStrategy.FIRST_SUCCESS,
    )
    result = await executor.execute(prompt)
"""

from __future__ import annotations

import asyncio
import difflib
import logging
import re
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from aurora_cli.file_change_aggregator import AggregationResult as FileAggregationResult
    from aurora_cli.file_change_aggregator import FileChangeAggregator  # noqa: F401
    from aurora_cli.tool_providers.base import ToolProvider

logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Strategy for aggregating results from multiple tools."""

    # Return first successful result, cancel others
    FIRST_SUCCESS = "first_success"

    # Wait for all tools to complete, return all results
    ALL_COMPLETE = "all_complete"

    # Return result agreed upon by majority (requires 3+ tools)
    VOTING = "voting"

    # Return best result based on custom scoring function
    BEST_SCORE = "best_score"

    # Merge outputs from all tools
    MERGE = "merge"

    # Intelligent merge with conflict resolution
    SMART_MERGE = "smart_merge"

    # Consensus: require agreement, report conflicts
    CONSENSUS = "consensus"


class ConflictSeverity(Enum):
    """Severity level for detected conflicts between tool outputs."""

    NONE = "none"  # No conflict detected
    FORMATTING = "formatting"  # Only whitespace/formatting differences
    MINOR = "minor"  # Small differences, likely equivalent
    MODERATE = "moderate"  # Noticeable differences, may need review
    MAJOR = "major"  # Significant disagreement between tools


@dataclass
class ConflictInfo:
    """Information about a conflict between tool outputs."""

    severity: ConflictSeverity
    tools_involved: list[str]
    description: str
    similarity_score: float  # 0.0 to 1.0
    diff_summary: str | None = None
    conflicting_sections: list[dict[str, Any]] = field(default_factory=list)


class ConflictDetector:
    """Detects and analyzes conflicts between tool outputs."""

    # Patterns to normalize for comparison (formatting-only differences)
    NORMALIZE_PATTERNS = [
        (r"\s+", " "),  # Multiple whitespace -> single space
        (r"^\s+|\s+$", ""),  # Leading/trailing whitespace
        (r"\n{3,}", "\n\n"),  # Multiple newlines -> double newline
    ]

    # Code block patterns for semantic comparison
    CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

    @classmethod
    def normalize_output(cls, text: str) -> str:
        """Normalize text for comparison, removing formatting differences."""
        result = text
        for pattern, replacement in cls.NORMALIZE_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result.strip()

    @classmethod
    def extract_code_blocks(cls, text: str) -> list[tuple[str, str]]:
        """Extract code blocks with their language tags."""
        return cls.CODE_BLOCK_PATTERN.findall(text)

    @classmethod
    def calculate_similarity(cls, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts (0.0 to 1.0)."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    @classmethod
    def get_diff_summary(cls, text1: str, text2: str, tool1: str, tool2: str) -> str:
        """Generate a human-readable diff summary."""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        diff = difflib.unified_diff(lines1, lines2, fromfile=tool1, tofile=tool2, n=2)
        diff_lines = list(diff)
        if len(diff_lines) > 20:
            return "".join(diff_lines[:20]) + f"\n... ({len(diff_lines) - 20} more lines)"
        return "".join(diff_lines)

    @classmethod
    def detect_conflicts(cls, results: list[ToolResult]) -> ConflictInfo:
        """Analyze tool results and detect conflicts."""
        successful = [r for r in results if r.success and r.output]
        if len(successful) < 2:
            return ConflictInfo(
                severity=ConflictSeverity.NONE,
                tools_involved=[r.tool for r in successful],
                description="Insufficient results for conflict detection",
                similarity_score=1.0,
            )

        # Normalize all outputs for comparison
        normalized = {r.tool: cls.normalize_output(r.output) for r in successful}

        # Calculate pairwise similarities
        similarities: list[tuple[str, str, float]] = []
        for i, r1 in enumerate(successful):
            for r2 in successful[i + 1 :]:
                sim = cls.calculate_similarity(normalized[r1.tool], normalized[r2.tool])
                similarities.append((r1.tool, r2.tool, sim))

        if not similarities:
            return ConflictInfo(
                severity=ConflictSeverity.NONE,
                tools_involved=[r.tool for r in successful],
                description="Single result, no conflicts",
                similarity_score=1.0,
            )

        # Calculate average similarity
        avg_sim = sum(s[2] for s in similarities) / len(similarities)

        # Determine severity based on similarity
        if avg_sim >= 0.95:
            severity = ConflictSeverity.NONE
            desc = "Outputs are nearly identical"
        elif avg_sim >= 0.85:
            # Check if differences are just formatting
            raw_similarities = []
            for r1 in successful:
                for r2 in successful:
                    if r1.tool < r2.tool:
                        raw_sim = cls.calculate_similarity(r1.output, r2.output)
                        raw_similarities.append(raw_sim)
            if raw_similarities and avg_sim - sum(raw_similarities) / len(raw_similarities) > 0.1:
                severity = ConflictSeverity.FORMATTING
                desc = "Differences are primarily formatting"
            else:
                severity = ConflictSeverity.MINOR
                desc = "Minor differences detected"
        elif avg_sim >= 0.60:
            severity = ConflictSeverity.MODERATE
            desc = "Moderate differences require review"
        else:
            severity = ConflictSeverity.MAJOR
            desc = "Significant disagreement between tools"

        # Find most conflicting pair for diff summary
        worst_pair = min(similarities, key=lambda x: x[2])
        t1, t2 = worst_pair[0], worst_pair[1]
        r1_output = next(r.output for r in successful if r.tool == t1)
        r2_output = next(r.output for r in successful if r.tool == t2)
        diff_summary = (
            cls.get_diff_summary(r1_output, r2_output, t1, t2)
            if severity not in (ConflictSeverity.NONE, ConflictSeverity.FORMATTING)
            else None
        )

        # Identify conflicting sections (code blocks, key statements)
        conflicting_sections = []
        if severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR):
            code1 = cls.extract_code_blocks(r1_output)
            code2 = cls.extract_code_blocks(r2_output)
            if code1 != code2:
                conflicting_sections.append(
                    {
                        "type": "code_blocks",
                        "tool1": t1,
                        "tool2": t2,
                        "count1": len(code1),
                        "count2": len(code2),
                    },
                )

        return ConflictInfo(
            severity=severity,
            tools_involved=[r.tool for r in successful],
            description=desc,
            similarity_score=avg_sim,
            diff_summary=diff_summary,
            conflicting_sections=conflicting_sections,
        )


class ConflictResolver:
    """Resolves conflicts between tool outputs using various strategies."""

    @classmethod
    def resolve_by_consensus(
        cls,
        results: list[ToolResult],
        threshold: float = 0.80,
    ) -> tuple[ToolResult | None, ConflictInfo]:
        """Find consensus among results. Returns None if no consensus reached."""
        conflict_info = ConflictDetector.detect_conflicts(results)

        if conflict_info.similarity_score >= threshold:
            # Consensus reached, return best result
            successful = [r for r in results if r.success]
            if successful:
                best = max(successful, key=lambda r: len(r.output))
                return best, conflict_info
        return None, conflict_info

    @classmethod
    def resolve_by_weighted_vote(
        cls,
        results: list[ToolResult],
        weights: dict[str, float] | None = None,
    ) -> tuple[ToolResult, ConflictInfo]:
        """Resolve using weighted voting. Each tool's output is weighted."""
        conflict_info = ConflictDetector.detect_conflicts(results)
        weights = weights or {}

        successful = [r for r in results if r.success]
        if not successful:
            return results[0] if results else None, conflict_info

        # Calculate weighted scores
        scores: dict[str, float] = {}
        for r in successful:
            base_weight = weights.get(r.tool, 1.0)
            # Boost for speed
            speed_bonus = max(0, (120 - r.execution_time) / 120) * 0.2
            # Boost for output completeness
            length_bonus = min(len(r.output) / 5000, 0.3)
            scores[r.tool] = base_weight + speed_bonus + length_bonus

        best_tool = max(scores, key=lambda t: scores[t])
        winner = next(r for r in successful if r.tool == best_tool)
        return winner, conflict_info

    @classmethod
    def smart_merge(
        cls,
        results: list[ToolResult],
    ) -> tuple[str, ConflictInfo]:
        """Intelligently merge outputs, preserving unique contributions."""
        conflict_info = ConflictDetector.detect_conflicts(results)
        successful = [r for r in results if r.success and r.output]

        if not successful:
            return "", conflict_info

        if len(successful) == 1:
            return successful[0].output, conflict_info

        # If outputs are very similar, just use the longest one
        if conflict_info.severity in (ConflictSeverity.NONE, ConflictSeverity.FORMATTING):
            best = max(successful, key=lambda r: len(r.output))
            return best.output, conflict_info

        # Extract unique sections from each output
        merged_sections: list[str] = []
        seen_content: set[str] = set()

        # Sort by output length descending (prefer more complete outputs)
        sorted_results = sorted(successful, key=lambda r: len(r.output), reverse=True)

        for r in sorted_results:
            # Split into paragraphs/sections
            sections = re.split(r"\n{2,}", r.output)
            for section in sections:
                normalized = ConflictDetector.normalize_output(section)
                if len(normalized) < 20:
                    continue
                # Check if this content is sufficiently different from what we have
                is_unique = True
                for seen in seen_content:
                    if ConflictDetector.calculate_similarity(normalized, seen) > 0.8:
                        is_unique = False
                        break
                if is_unique:
                    merged_sections.append(section)
                    seen_content.add(normalized)

        if not merged_sections:
            return successful[0].output, conflict_info

        # Add header indicating merge
        header = f"# Merged Output from {len(successful)} tools\n\n"
        header += f"**Conflict severity**: {conflict_info.severity.value}\n"
        header += f"**Similarity score**: {conflict_info.similarity_score:.2%}\n\n---\n\n"

        return header + "\n\n".join(merged_sections), conflict_info


@dataclass
class ToolResult:
    """Result from a single tool execution."""

    tool: str
    success: bool
    output: str
    error: str | None = None
    exit_code: int = 0
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    parsed_output: Any = None  # ParsedOutput from tool provider


@dataclass
class AggregatedResult:
    """Aggregated result from multiple tool executions."""

    success: bool
    primary_output: str
    strategy_used: AggregationStrategy
    tool_results: list[ToolResult]
    execution_time: float = 0.0
    winning_tool: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    conflict_info: ConflictInfo | None = None
    file_changes: FileAggregationResult | None = None


@dataclass
class ToolConfig:
    """Configuration for a specific tool."""

    name: str
    command: list[str] | None = None  # Custom command, uses [name, "-p"] if None
    timeout: float = 600.0  # 10 minutes default
    weight: float = 1.0  # Weight for voting/scoring
    enabled: bool = True
    input_mode: str = "stdin"  # "stdin" or "arg"


class ConcurrentToolExecutor:
    """Execute prompts across multiple AI tools concurrently.

    Supports running the same prompt with multiple tools (Claude, OpenCode, etc.)
    in parallel and aggregating results using various strategies.

    Features:
    - Multiple aggregation strategies (first_success, all_complete, voting, etc.)
    - Optional resource isolation (working directory, environment, concurrency)
    - Conflict detection and resolution between tool outputs
    - Custom scoring functions for result selection

    Attributes:
        tools: List of tool configurations
        strategy: Aggregation strategy for combining results
        timeout: Global timeout for all executions
        scratchpad_path: Optional path for shared scratchpad
        isolation_level: Resource isolation level ("none", "light", "full")

    """

    def __init__(
        self,
        tools: list[str | ToolConfig],
        strategy: AggregationStrategy = AggregationStrategy.FIRST_SUCCESS,
        timeout: float = 600.0,
        scratchpad_path: Path | None = None,
        scorer: Callable[[ToolResult], float] | None = None,
        isolation_level: str = "none",
        max_concurrent: int = 5,
        max_per_tool: int = 2,
        track_file_changes: bool = False,
        working_dir: Path | None = None,
    ):
        """Initialize concurrent executor.

        Args:
            tools: List of tool names or ToolConfig objects
            strategy: How to aggregate results from multiple tools
            timeout: Global timeout in seconds
            scratchpad_path: Optional shared scratchpad path
            scorer: Custom scoring function for BEST_SCORE strategy
            isolation_level: Resource isolation level ("none", "light", "full")
            max_concurrent: Maximum concurrent tool executions
            max_per_tool: Maximum concurrent executions per tool type
            track_file_changes: Enable file change tracking and conflict resolution
            working_dir: Working directory for file change tracking

        """
        self.tools = self._normalize_tools(tools)
        self.strategy = strategy
        self.timeout = timeout
        self.scratchpad_path = scratchpad_path
        self.scorer = scorer or self._default_scorer
        self.isolation_level = isolation_level
        self.max_concurrent = max_concurrent
        self.max_per_tool = max_per_tool
        self.track_file_changes = track_file_changes
        self.working_dir = working_dir or Path.cwd()

        # Resource isolation manager (created lazily if needed)
        self._isolation_manager: Any = None

        # File change aggregator (created lazily if tracking enabled)
        self._file_aggregator: FileChangeAggregator | None = None
        if self.track_file_changes:
            from aurora_cli.file_change_aggregator import FileChangeAggregator  # noqa: F811

            self._file_aggregator = FileChangeAggregator(working_dir=self.working_dir)

        # Validate tools exist
        self._validate_tools()

    def _normalize_tools(self, tools: list[str | ToolConfig]) -> list[ToolConfig]:
        """Convert tool names to ToolConfig objects."""
        result = []
        for tool in tools:
            if isinstance(tool, str):
                result.append(ToolConfig(name=tool))
            else:
                result.append(tool)
        return result

    def _validate_tools(self) -> None:
        """Validate all tools exist in PATH or registry."""
        from aurora_cli.tool_providers import ToolProviderRegistry

        registry = ToolProviderRegistry.get_instance()
        missing = []

        for tool in self.tools:
            if not tool.enabled:
                continue

            # First check registry for provider
            provider = registry.get(tool.name)
            if provider and provider.is_available():
                continue

            # Fallback to PATH check
            if not shutil.which(tool.name):
                missing.append(tool.name)

        if missing:
            raise ValueError(f"Tools not found in PATH: {', '.join(missing)}")

    def _default_scorer(self, result: ToolResult) -> float:
        """Default scoring function for BEST_SCORE strategy.

        Scores based on:
        - Success (10 points)
        - Output length (1 point per 100 chars, max 5)
        - Speed (faster is better, max 3 points)
        """
        score = 0.0

        if result.success:
            score += 10.0

        # Output length (more content = better, up to a point)
        output_len = len(result.output)
        score += min(output_len / 100, 5.0)

        # Speed bonus (faster = better)
        if result.execution_time < 30:
            score += 3.0
        elif result.execution_time < 60:
            score += 2.0
        elif result.execution_time < 120:
            score += 1.0

        return score

    def _get_isolation_manager(self):
        """Get or create the resource isolation manager."""
        if self._isolation_manager is None and self.isolation_level != "none":
            from aurora_cli.resource_isolation import (
                IsolationConfig,
                IsolationLevel,
                ResourceIsolationManager,
                ResourceLimits,
            )

            config = IsolationConfig(
                level=IsolationLevel(self.isolation_level),
                limits=ResourceLimits(
                    max_concurrent=self.max_concurrent,
                    max_per_tool=self.max_per_tool,
                ),
            )
            self._isolation_manager = ResourceIsolationManager(config)

        return self._isolation_manager

    async def _execute_tool(
        self,
        tool: ToolConfig,
        prompt: str,
        cancel_event: asyncio.Event | None = None,
    ) -> ToolResult:
        """Execute prompt with a single tool.

        Uses ToolProviderRegistry when a provider is available for the tool,
        otherwise falls back to direct subprocess execution.

        If isolation is enabled, wraps execution in an isolation context.

        Args:
            tool: Tool configuration
            prompt: Prompt to execute
            cancel_event: Optional event to cancel execution

        Returns:
            ToolResult with execution details

        """
        isolation_manager = self._get_isolation_manager()

        if isolation_manager is not None:
            return await self._execute_with_isolation(tool, prompt, cancel_event, isolation_manager)

        return await self._execute_tool_internal(tool, prompt, cancel_event)

    async def _execute_with_isolation(
        self,
        tool: ToolConfig,
        prompt: str,
        cancel_event: asyncio.Event | None,
        isolation_manager,
    ) -> ToolResult:
        """Execute tool with resource isolation.

        Args:
            tool: Tool configuration
            prompt: Prompt to execute
            cancel_event: Optional event to cancel execution
            isolation_manager: ResourceIsolationManager instance

        Returns:
            ToolResult with execution details

        """
        start_time = time.time()

        try:
            async with isolation_manager.isolated_execution(tool.name) as context:
                # Execute within isolated context
                result = await self._execute_tool_internal(tool, prompt, cancel_event, context)
                result.metadata["isolation"] = {
                    "execution_id": context.execution_id,
                    "working_dir": str(context.working_dir),
                    "level": context.metadata.get("isolation_level", "unknown"),
                }
                return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {tool.name} isolation error: {e}")
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=f"Isolation error: {e}",
                exit_code=-1,
                execution_time=execution_time,
                metadata={"isolation_error": True},
            )

    async def _execute_tool_internal(
        self,
        tool: ToolConfig,
        prompt: str,
        _cancel_event: asyncio.Event | None = None,
        context: Any = None,
    ) -> ToolResult:
        """Internal tool execution logic.

        Args:
            tool: Tool configuration
            prompt: Prompt to execute
            cancel_event: Optional event to cancel execution
            context: Optional ExecutionContext for isolation

        Returns:
            ToolResult with execution details

        """
        from aurora_cli.tool_providers import ToolProviderRegistry

        start_time = time.time()

        # Extract working directory and environment from context if available
        working_dir = None
        env = None
        if context is not None:
            working_dir = context.working_dir
            env = context.environment

        # Try to use registered tool provider first
        registry = ToolProviderRegistry.get_instance()
        provider = registry.get(tool.name)

        if provider and provider.is_available():
            return await self._execute_with_provider(
                provider,
                tool,
                prompt,
                start_time,
                working_dir,
                env,
            )

        # Fallback to direct subprocess execution
        return await self._execute_direct(tool, prompt, start_time, working_dir, env)

    async def _execute_with_provider(
        self,
        provider: ToolProvider,
        tool: ToolConfig,
        prompt: str,
        start_time: float,
        working_dir: Path | None = None,
        _env: dict[str, str] | None = None,
    ) -> ToolResult:
        """Execute using a registered tool provider with retry support.

        Args:
            provider: Tool provider instance
            tool: Tool configuration
            prompt: Prompt to execute
            start_time: Execution start time
            working_dir: Optional working directory for isolated execution
            env: Optional environment variables for isolated execution

        Returns:
            ToolResult with execution details

        """
        try:
            # Use provider's retry-enabled async execution
            result = await provider.execute_async_with_retry(
                prompt,
                working_dir=working_dir,
                timeout=int(tool.timeout),
            )

            execution_time = time.time() - start_time

            # Parse output using provider's output handler if available
            parsed_output = None
            if hasattr(provider, "parse_output"):
                try:
                    parsed_output = provider.parse_output(result.stdout)
                except Exception as parse_err:
                    logger.debug(f"Failed to parse {tool.name} output: {parse_err}")

            # Include retry info in metadata
            metadata = result.metadata.copy() if result.metadata else {}

            return ToolResult(
                tool=tool.name,
                success=result.success,
                output=result.stdout,
                error=result.stderr if not result.success else None,
                exit_code=result.return_code,
                execution_time=execution_time,
                parsed_output=parsed_output,
                metadata=metadata,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=f"Timeout after {tool.timeout}s",
                exit_code=-1,
                execution_time=execution_time,
            )
        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error="Cancelled",
                exit_code=-2,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {tool.name} provider execution error: {e}")
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                execution_time=execution_time,
            )

    async def _execute_direct(
        self,
        tool: ToolConfig,
        prompt: str,
        start_time: float,
        working_dir: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> ToolResult:
        """Execute tool directly via subprocess (fallback).

        Args:
            tool: Tool configuration
            prompt: Prompt to execute
            start_time: Execution start time
            working_dir: Optional working directory for isolated execution
            env: Optional environment variables for isolated execution

        Returns:
            ToolResult with execution details

        """
        # Build command
        if tool.command:
            cmd = tool.command.copy()
        else:
            # Tool-specific command building
            if tool.name == "claude":
                cmd = [tool.name, "--print", "--dangerously-skip-permissions"]
                if tool.input_mode == "arg":
                    cmd.append(prompt)
            elif tool.name == "opencode":
                # OpenCode uses stdin
                cmd = [tool.name]
            else:
                # Default case with pipe mode
                cmd = [tool.name, "-p"]

        # Prepare subprocess kwargs
        subprocess_kwargs: dict[str, Any] = {
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
        }
        if working_dir is not None:
            subprocess_kwargs["cwd"] = str(working_dir)
        if env is not None:
            subprocess_kwargs["env"] = env

        try:
            # Create subprocess
            if tool.input_mode == "stdin" or (tool.name == "claude" and tool.input_mode != "arg"):
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    **subprocess_kwargs,
                )

                # Write prompt to stdin
                if tool.name == "claude" and tool.input_mode == "arg":
                    # Claude with --print uses argument
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=tool.timeout,
                    )
                else:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=prompt.encode()),
                        timeout=tool.timeout,
                    )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    **subprocess_kwargs,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=tool.timeout,
                )

            execution_time = time.time() - start_time
            output = stdout.decode(errors="ignore")

            # Try to parse output using the output handler
            parsed_output = None
            try:
                from aurora_cli.tool_providers.output_handler import get_handler

                handler = get_handler(tool.name)
                parsed_output = handler.parse(output)
            except Exception as parse_err:
                logger.debug(f"Failed to parse {tool.name} output: {parse_err}")

            return ToolResult(
                tool=tool.name,
                success=process.returncode == 0,
                output=output,
                error=stderr.decode(errors="ignore") if process.returncode != 0 else None,
                exit_code=process.returncode or 0,
                execution_time=execution_time,
                parsed_output=parsed_output,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=f"Timeout after {tool.timeout}s",
                exit_code=-1,
                execution_time=execution_time,
            )
        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error="Cancelled",
                exit_code=-2,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {tool.name} execution error: {e}")
            return ToolResult(
                tool=tool.name,
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
                execution_time=execution_time,
            )

    async def execute(self, prompt: str) -> AggregatedResult:
        """Execute prompt with all tools using configured strategy.

        Args:
            prompt: Prompt to execute

        Returns:
            AggregatedResult with combined results

        """
        start_time = time.time()
        enabled_tools = [t for t in self.tools if t.enabled]

        if not enabled_tools:
            return AggregatedResult(
                success=False,
                primary_output="",
                strategy_used=self.strategy,
                tool_results=[],
                metadata={"error": "No tools enabled"},
            )

        # Capture file state before execution if tracking enabled
        if self._file_aggregator:
            self._file_aggregator.capture_before()

        # Execute based on strategy
        if self.strategy == AggregationStrategy.FIRST_SUCCESS:
            result = await self._execute_first_success(enabled_tools, prompt)
        elif self.strategy == AggregationStrategy.ALL_COMPLETE:
            result = await self._execute_all_complete(enabled_tools, prompt)
        elif self.strategy == AggregationStrategy.VOTING:
            result = await self._execute_voting(enabled_tools, prompt)
        elif self.strategy == AggregationStrategy.BEST_SCORE:
            result = await self._execute_best_score(enabled_tools, prompt)
        elif self.strategy == AggregationStrategy.MERGE:
            result = await self._execute_merge(enabled_tools, prompt)
        elif self.strategy == AggregationStrategy.SMART_MERGE:
            result = await self._execute_smart_merge(enabled_tools, prompt)
        elif self.strategy == AggregationStrategy.CONSENSUS:
            result = await self._execute_consensus(enabled_tools, prompt)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # Aggregate file changes if tracking enabled
        if self._file_aggregator:
            result.file_changes = self._aggregate_file_changes(result.tool_results)

        result.execution_time = time.time() - start_time
        return result

    def _aggregate_file_changes(
        self,
        tool_results: list[ToolResult],
    ) -> FileAggregationResult | None:
        """Aggregate file changes from all tool executions.

        Args:
            tool_results: Results from tool executions

        Returns:
            FileAggregationResult with merged changes and conflict info

        """
        if not self._file_aggregator:
            return None

        from aurora_cli.file_change_aggregator import MergeStrategy

        # Capture changes for each successful tool
        for tr in tool_results:
            if tr.success:
                self._file_aggregator.capture_after(tr.tool)

        # Resolve conflicts based on aggregation strategy
        merge_strategy = MergeStrategy.PREFER_FIRST
        if self.strategy == AggregationStrategy.SMART_MERGE:
            merge_strategy = MergeStrategy.SMART_MERGE
        elif self.strategy == AggregationStrategy.MERGE:
            merge_strategy = MergeStrategy.UNION
        elif self.strategy == AggregationStrategy.CONSENSUS:
            merge_strategy = MergeStrategy.SMART_MERGE

        return self._file_aggregator.resolve(strategy=merge_strategy)

    async def _execute_first_success(
        self,
        tools: list[ToolConfig],
        prompt: str,
    ) -> AggregatedResult:
        """Execute tools in parallel, return first successful result."""
        cancel_event = asyncio.Event()
        tasks = {
            asyncio.create_task(self._execute_tool(tool, prompt, cancel_event)): tool
            for tool in tools
        }

        results: list[ToolResult] = []
        winner: ToolResult | None = None

        try:
            for coro in asyncio.as_completed(tasks.keys()):
                result = await coro
                results.append(result)

                if result.success and winner is None:
                    winner = result
                    cancel_event.set()
                    # Cancel remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break

        except asyncio.CancelledError:
            pass

        # Collect any remaining results
        for task in tasks:
            if task.done() and not task.cancelled():
                try:
                    result = task.result()
                    if result not in results:
                        results.append(result)
                except Exception:
                    pass

        if winner:
            return AggregatedResult(
                success=True,
                primary_output=winner.output,
                strategy_used=self.strategy,
                tool_results=results,
                winning_tool=winner.tool,
            )

        # No success, return first result
        return AggregatedResult(
            success=False,
            primary_output=results[0].output if results else "",
            strategy_used=self.strategy,
            tool_results=results,
            metadata={"error": "All tools failed"},
        )

    async def _execute_all_complete(
        self,
        tools: list[ToolConfig],
        prompt: str,
    ) -> AggregatedResult:
        """Execute all tools and wait for completion."""
        tasks = [self._execute_tool(tool, prompt) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        tool_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_results.append(
                    ToolResult(
                        tool=tools[i].name,
                        success=False,
                        output="",
                        error=str(result),
                        exit_code=-1,
                    ),
                )
            else:
                tool_results.append(result)

        # Find best result
        successful = [r for r in tool_results if r.success]
        if successful:
            # Return result with most output
            best = max(successful, key=lambda r: len(r.output))
            return AggregatedResult(
                success=True,
                primary_output=best.output,
                strategy_used=self.strategy,
                tool_results=tool_results,
                winning_tool=best.tool,
            )

        return AggregatedResult(
            success=False,
            primary_output=tool_results[0].output if tool_results else "",
            strategy_used=self.strategy,
            tool_results=tool_results,
        )

    async def _execute_voting(
        self,
        tools: list[ToolConfig],
        prompt: str,
    ) -> AggregatedResult:
        """Execute all tools and use voting for consensus."""
        if len(tools) < 3:
            logger.warning("Voting requires 3+ tools, falling back to ALL_COMPLETE")
            return await self._execute_all_complete(tools, prompt)

        results = await self._execute_all_complete(tools, prompt)

        # Simple voting: count similar outputs
        # For now, just return the most common successful output
        successful = [r for r in results.tool_results if r.success]
        if not successful:
            return results

        # Group by output similarity (exact match for simplicity)
        votes: dict[str, list[ToolResult]] = {}
        for r in successful:
            # Normalize output for comparison
            key = r.output.strip()[:1000]  # First 1000 chars
            if key not in votes:
                votes[key] = []
            votes[key].append(r)

        # Find majority
        winner_group = max(votes.values(), key=len)
        winner = winner_group[0]

        return AggregatedResult(
            success=True,
            primary_output=winner.output,
            strategy_used=self.strategy,
            tool_results=results.tool_results,
            winning_tool=winner.tool,
            metadata={"votes": {k[:50]: len(v) for k, v in votes.items()}},
        )

    async def _execute_best_score(
        self,
        tools: list[ToolConfig],
        prompt: str,
    ) -> AggregatedResult:
        """Execute all tools and return best scored result."""
        results = await self._execute_all_complete(tools, prompt)

        # Score all results
        scored = [(self.scorer(r), r) for r in results.tool_results]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_result = scored[0]

        return AggregatedResult(
            success=best_result.success,
            primary_output=best_result.output,
            strategy_used=self.strategy,
            tool_results=results.tool_results,
            winning_tool=best_result.tool,
            metadata={"scores": {r.tool: s for s, r in scored}},
        )

    async def _execute_merge(
        self,
        tools: list[ToolConfig],
        prompt: str,
    ) -> AggregatedResult:
        """Execute all tools and merge outputs."""
        results = await self._execute_all_complete(tools, prompt)

        # Merge successful outputs
        successful = [r for r in results.tool_results if r.success]
        if not successful:
            return AggregatedResult(
                success=False,
                primary_output="",
                strategy_used=self.strategy,
                tool_results=results.tool_results,
            )

        # Simple merge: concatenate with headers
        merged_parts = []
        for r in successful:
            merged_parts.append(f"=== {r.tool} ===\n{r.output}")

        return AggregatedResult(
            success=True,
            primary_output="\n\n".join(merged_parts),
            strategy_used=self.strategy,
            tool_results=results.tool_results,
            metadata={"merged_count": len(successful)},
        )

    async def _execute_smart_merge(
        self,
        tools: list[ToolConfig],
        prompt: str,
    ) -> AggregatedResult:
        """Execute all tools and intelligently merge outputs with conflict detection."""
        results = await self._execute_all_complete(tools, prompt)

        # Use ConflictResolver for intelligent merging
        merged_output, conflict_info = ConflictResolver.smart_merge(results.tool_results)

        if not merged_output:
            return AggregatedResult(
                success=False,
                primary_output="",
                strategy_used=self.strategy,
                tool_results=results.tool_results,
                conflict_info=conflict_info,
                metadata={"error": "No successful outputs to merge"},
            )

        successful = [r for r in results.tool_results if r.success]
        return AggregatedResult(
            success=True,
            primary_output=merged_output,
            strategy_used=self.strategy,
            tool_results=results.tool_results,
            conflict_info=conflict_info,
            metadata={
                "merged_count": len(successful),
                "conflict_severity": conflict_info.severity.value,
                "similarity_score": conflict_info.similarity_score,
            },
        )

    async def _execute_consensus(
        self,
        tools: list[ToolConfig],
        prompt: str,
        threshold: float = 0.80,
    ) -> AggregatedResult:
        """Execute all tools and require consensus for success.

        Returns the best result if consensus is reached (similarity >= threshold),
        otherwise reports the conflict and returns all results for review.
        """
        results = await self._execute_all_complete(tools, prompt)

        # Get tool weights from configs
        weights = {t.name: t.weight for t in tools}

        # Try consensus resolution
        winner, conflict_info = ConflictResolver.resolve_by_consensus(
            results.tool_results,
            threshold=threshold,
        )

        if winner:
            return AggregatedResult(
                success=True,
                primary_output=winner.output,
                strategy_used=self.strategy,
                tool_results=results.tool_results,
                winning_tool=winner.tool,
                conflict_info=conflict_info,
                metadata={
                    "consensus_reached": True,
                    "similarity_score": conflict_info.similarity_score,
                    "threshold": threshold,
                },
            )

        # No consensus - fall back to weighted vote but mark as conflict
        winner, _ = ConflictResolver.resolve_by_weighted_vote(results.tool_results, weights)

        return AggregatedResult(
            success=True,  # Still successful, but with conflicts
            primary_output=winner.output if winner else "",
            strategy_used=self.strategy,
            tool_results=results.tool_results,
            winning_tool=winner.tool if winner else None,
            conflict_info=conflict_info,
            metadata={
                "consensus_reached": False,
                "similarity_score": conflict_info.similarity_score,
                "threshold": threshold,
                "conflict_severity": conflict_info.severity.value,
                "resolution_method": "weighted_vote",
            },
        )


def run_concurrent(
    prompt: str,
    tools: list[str],
    strategy: str = "first_success",
    timeout: float = 600.0,
) -> AggregatedResult:
    """Synchronous wrapper for concurrent execution.

    Args:
        prompt: Prompt to execute
        tools: List of tool names
        strategy: Aggregation strategy name
        timeout: Global timeout

    Returns:
        AggregatedResult

    """
    strategy_enum = AggregationStrategy(strategy)
    executor = ConcurrentToolExecutor(tools, strategy=strategy_enum, timeout=timeout)
    return asyncio.run(executor.execute(prompt))
