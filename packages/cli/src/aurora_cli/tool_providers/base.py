"""Base classes for tool providers."""

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class ToolStatus(Enum):
    """Status of a tool execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"


class InputMethod(Enum):
    """How the tool receives input."""

    ARGUMENT = "argument"  # Context passed as command-line argument
    STDIN = "stdin"  # Context passed via stdin
    FILE = "file"  # Context written to temporary file
    PIPE = "pipe"  # Context piped to tool


class OutputFormat(Enum):
    """Format of tool output for normalization."""

    RAW = "raw"  # Output as-is from tool
    MARKDOWN = "markdown"  # Markdown formatted
    JSON = "json"  # JSON structured
    STREAMING = "streaming"  # Streaming chunks


@runtime_checkable
class ToolAdapter(Protocol):
    """Protocol for tool adapters enabling duck-typed tool implementations.

    This protocol defines the minimal interface required for a tool to work
    with the headless command and concurrent executor. Implementations can
    be either class-based (ToolProvider subclass) or config-based (GenericToolProvider).
    """

    @property
    def name(self) -> str:
        """Unique identifier for the tool."""
        ...

    def is_available(self) -> bool:
        """Check if the tool is installed and accessible."""
        ...

    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> "ToolResult":
        """Execute the tool with given context."""
        ...


@dataclass
class ToolResult:
    """Result of a tool execution."""

    status: ToolStatus
    stdout: str
    stderr: str
    return_code: int
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ToolStatus.SUCCESS and self.return_code == 0


@dataclass
class ToolCapabilities:
    """Capabilities and features supported by a tool provider."""

    supports_streaming: bool = False
    supports_conversation: bool = False
    supports_system_prompt: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    max_context_length: int | None = None
    default_timeout: int = 600
    priority: int = 100  # Lower = higher priority

    def matches(self, required: "ToolCapabilities") -> bool:
        """Check if this capability set satisfies required capabilities.

        Args:
            required: Required capabilities to check against

        Returns:
            True if all required capabilities are met

        """
        if required.supports_streaming and not self.supports_streaming:
            return False
        if required.supports_conversation and not self.supports_conversation:
            return False
        if required.supports_system_prompt and not self.supports_system_prompt:
            return False
        if required.supports_tools and not self.supports_tools:
            return False
        if required.supports_vision and not self.supports_vision:
            return False
        if required.max_context_length is not None:
            if self.max_context_length is None:
                return False
            if self.max_context_length < required.max_context_length:
                return False
        return True


class OutputNormalizer:
    """Utility class for normalizing tool output across different providers.

    Handles common output transformations like stripping ANSI codes,
    normalizing whitespace, and extracting structured content.
    """

    # ANSI escape code pattern
    ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

    # Common tool output prefixes to strip
    NOISE_PATTERNS = [
        re.compile(r"^[\s\S]*?(```)", re.MULTILINE),  # Content before first code block
        re.compile(r"^\s*\[.*?\]\s*", re.MULTILINE),  # Progress indicators like [1/5]
        re.compile(r"^\s*(?:INFO|DEBUG|WARN):\s*", re.MULTILINE),  # Log prefixes
    ]

    @classmethod
    def strip_ansi(cls, text: str) -> str:
        """Remove ANSI escape codes from text."""
        return cls.ANSI_PATTERN.sub("", text)

    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Normalize whitespace without destroying structure."""
        # Replace multiple blank lines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    @classmethod
    def extract_code_blocks(cls, text: str) -> list[tuple[str, str]]:
        """Extract code blocks with their language tags.

        Returns:
            List of (language, code) tuples

        """
        pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        return pattern.findall(text)

    @classmethod
    def extract_main_content(cls, text: str) -> str:
        """Extract main content, removing tool-specific noise."""
        result = text
        for pattern in cls.NOISE_PATTERNS:
            # Only apply if pattern doesn't destroy too much content
            cleaned = pattern.sub("", result)
            if len(cleaned) > len(result) * 0.5:  # Keep at least 50%
                result = cleaned
        return result.strip()

    @classmethod
    def normalize(cls, text: str, strip_ansi: bool = True) -> str:
        """Full normalization pipeline.

        Args:
            text: Raw tool output
            strip_ansi: Whether to strip ANSI codes

        Returns:
            Normalized text

        """
        if not text:
            return ""

        result = text
        if strip_ansi:
            result = cls.strip_ansi(result)
        result = cls.normalize_whitespace(result)
        return result


class CapabilityRouter:
    """Routes tasks to tools based on required capabilities.

    Provides capability-based tool selection for multi-tool scenarios.
    """

    @staticmethod
    def select_tools(
        available: list["ToolProvider"],
        required: ToolCapabilities,
        max_tools: int | None = None,
    ) -> list["ToolProvider"]:
        """Select tools that match required capabilities.

        Args:
            available: List of available tool providers
            required: Required capabilities
            max_tools: Maximum number of tools to return

        Returns:
            List of matching providers sorted by priority

        """
        matching = [p for p in available if p.is_available() and p.capabilities.matches(required)]
        # Sort by priority (lower is better)
        matching.sort(key=lambda p: p.priority)
        if max_tools is not None:
            return matching[:max_tools]
        return matching

    @staticmethod
    def select_best(
        available: list["ToolProvider"],
        required: ToolCapabilities,
    ) -> "ToolProvider | None":
        """Select the best single tool for the task.

        Args:
            available: List of available tool providers
            required: Required capabilities

        Returns:
            Best matching provider or None

        """
        matching = CapabilityRouter.select_tools(available, required, max_tools=1)
        return matching[0] if matching else None

    @staticmethod
    def group_by_capability(
        providers: list["ToolProvider"],
    ) -> dict[str, list["ToolProvider"]]:
        """Group providers by their primary capabilities.

        Returns:
            Dict mapping capability names to providers

        """
        groups: dict[str, list[ToolProvider]] = {
            "streaming": [],
            "conversation": [],
            "system_prompt": [],
            "tools": [],
            "vision": [],
            "large_context": [],
        }

        for p in providers:
            caps = p.capabilities
            if caps.supports_streaming:
                groups["streaming"].append(p)
            if caps.supports_conversation:
                groups["conversation"].append(p)
            if caps.supports_system_prompt:
                groups["system_prompt"].append(p)
            if caps.supports_tools:
                groups["tools"].append(p)
            if caps.supports_vision:
                groups["vision"].append(p)
            if caps.max_context_length and caps.max_context_length >= 100000:
                groups["large_context"].append(p)

        return groups


class ToolProvider(ABC):
    """Abstract base class for AI tool providers.

    Implementations must provide:
    - name: Unique identifier for the tool
    - is_available(): Check if tool is installed and accessible
    - execute(): Run the tool with given context
    - build_command(): Construct the command for execution

    Optional overrides:
    - display_name: Human-readable name
    - executable: CLI binary name (defaults to name)
    - input_method: How context is passed to the tool
    - capabilities: Tool features and limits
    - default_flags: Default command-line flags
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize provider with optional configuration override.

        Args:
            config: Optional configuration dict to override defaults.
                   Supports keys: timeout, flags, input_method, priority

        """
        self._config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name/identifier of the tool."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for display purposes."""
        return self.name.capitalize()

    @property
    def executable(self) -> str:
        """CLI binary name. Override if different from name."""
        return self.name

    @property
    def input_method(self) -> InputMethod:
        """How context is passed to the tool. Override as needed."""
        # Check config override first
        if "input_method" in self._config:
            return InputMethod(self._config["input_method"])
        return InputMethod.STDIN

    @property
    def capabilities(self) -> ToolCapabilities:
        """Tool capabilities and limits. Override as needed."""
        return ToolCapabilities()

    @property
    def default_flags(self) -> list[str]:
        """Default command-line flags. Override as needed."""
        # Config can override or extend default flags
        if "flags" in self._config:
            return list(self._config["flags"])
        return []

    @property
    def extra_flags(self) -> list[str]:
        """Extra flags from CLI overrides (appended to default_flags)."""
        if "extra_flags" in self._config:
            return list(self._config["extra_flags"])
        return []

    @property
    def all_flags(self) -> list[str]:
        """Combined default_flags + extra_flags."""
        return self.default_flags + self.extra_flags

    @property
    def env_overrides(self) -> dict[str, str]:
        """Environment variable overrides from config."""
        if "env" in self._config:
            return dict(self._config["env"])
        return {}

    @property
    def timeout(self) -> int:
        """Default timeout for this tool."""
        if "timeout" in self._config:
            return int(self._config["timeout"])
        return self.capabilities.default_timeout

    @property
    def priority(self) -> int:
        """Tool priority (lower = higher priority)."""
        if "priority" in self._config:
            return int(self._config["priority"])
        return self.capabilities.priority

    @property
    def max_retries(self) -> int:
        """Maximum retry attempts on failure."""
        if "max_retries" in self._config:
            return int(self._config["max_retries"])
        return 2  # Default

    @property
    def retry_delay(self) -> float:
        """Base delay between retries in seconds."""
        if "retry_delay" in self._config:
            return float(self._config["retry_delay"])
        return 1.0  # Default

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the tool is installed and available in PATH."""
        ...

    @abstractmethod
    def execute(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute the tool with the given context.

        Args:
            context: The prompt/context to pass to the tool
            working_dir: Working directory for execution (default: cwd)
            timeout: Maximum execution time in seconds (default: 600)

        Returns:
            ToolResult with execution status and output

        """
        ...

    @abstractmethod
    def build_command(self, context: str) -> list[str]:
        """Build the command line arguments for execution.

        Args:
            context: The prompt/context to pass to the tool

        Returns:
            List of command line arguments

        """
        ...

    def execute_with_retry(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> ToolResult:
        """Execute the tool with retry logic on failure.

        Retries on transient failures with exponential backoff.
        Non-retryable errors (NOT_FOUND, timeouts) are not retried.

        Args:
            context: The prompt/context to pass to the tool
            working_dir: Working directory for execution
            timeout: Maximum execution time in seconds
            max_retries: Override max retry attempts (default: from config)
            retry_delay: Override base retry delay (default: from config)

        Returns:
            ToolResult with execution status and output

        """
        import logging
        import time

        logger = logging.getLogger(__name__)
        retries = max_retries if max_retries is not None else self.max_retries
        delay = retry_delay if retry_delay is not None else self.retry_delay

        last_result: ToolResult | None = None

        for attempt in range(retries + 1):  # Initial attempt + retries
            result = self.execute(context, working_dir, timeout)
            last_result = result

            # Success or non-retryable error
            if result.success:
                if attempt > 0:
                    result.metadata["retry_attempts"] = attempt
                return result

            # Non-retryable statuses
            if result.status in (ToolStatus.NOT_FOUND, ToolStatus.TIMEOUT):
                logger.debug(f"{self.name}: Non-retryable status {result.status.value}")
                return result

            # Check if this was the last attempt
            if attempt >= retries:
                logger.debug(f"{self.name}: Max retries ({retries}) exhausted")
                result.metadata["retry_attempts"] = attempt
                return result

            # Calculate backoff delay (exponential with jitter)
            import random

            backoff = delay * (2**attempt) + random.uniform(0, 0.5)
            logger.info(f"{self.name}: Attempt {attempt + 1} failed, retrying in {backoff:.2f}s")
            time.sleep(backoff)

        # Should not reach here, but return last result as fallback
        return last_result or ToolResult(
            status=ToolStatus.FAILURE,
            stdout="",
            stderr="Retry logic error",
            return_code=-1,
        )

    async def execute_async(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
    ) -> ToolResult:
        """Execute the tool asynchronously.

        Default implementation wraps synchronous execute() in a thread pool.
        Override for native async implementations.

        Args:
            context: The prompt/context to pass to the tool
            working_dir: Working directory for execution
            timeout: Maximum execution time in seconds

        Returns:
            ToolResult with execution status and output

        """
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: self.execute(context, working_dir, timeout)),
            timeout=timeout,
        )

    async def execute_async_with_retry(
        self,
        context: str,
        working_dir: Path | None = None,
        timeout: int = 600,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> ToolResult:
        """Execute the tool asynchronously with retry logic.

        Args:
            context: The prompt/context to pass to the tool
            working_dir: Working directory for execution
            timeout: Maximum execution time in seconds
            max_retries: Override max retry attempts (default: from config)
            retry_delay: Override base retry delay (default: from config)

        Returns:
            ToolResult with execution status and output

        """
        import logging

        logger = logging.getLogger(__name__)
        retries = max_retries if max_retries is not None else self.max_retries
        delay = retry_delay if retry_delay is not None else self.retry_delay

        last_result: ToolResult | None = None

        for attempt in range(retries + 1):
            try:
                result = await self.execute_async(context, working_dir, timeout)
                last_result = result

                if result.success:
                    if attempt > 0:
                        result.metadata["retry_attempts"] = attempt
                    return result

                # Non-retryable statuses
                if result.status in (ToolStatus.NOT_FOUND, ToolStatus.TIMEOUT):
                    return result

                if attempt >= retries:
                    result.metadata["retry_attempts"] = attempt
                    return result

                # Calculate backoff
                import random

                backoff = delay * (2**attempt) + random.uniform(0, 0.5)
                logger.info(
                    f"{self.name}: Async attempt {attempt + 1} failed, retrying in {backoff:.2f}s",
                )
                await asyncio.sleep(backoff)

            except asyncio.TimeoutError:
                return ToolResult(
                    status=ToolStatus.TIMEOUT,
                    stdout="",
                    stderr=f"Async execution timed out after {timeout}s",
                    return_code=-1,
                    metadata={"retry_attempts": attempt},
                )
            except asyncio.CancelledError:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    stdout="",
                    stderr="Async execution cancelled",
                    return_code=-2,
                    metadata={"retry_attempts": attempt},
                )

        return last_result or ToolResult(
            status=ToolStatus.FAILURE,
            stdout="",
            stderr="Async retry logic error",
            return_code=-1,
        )

    @property
    def output_format(self) -> OutputFormat:
        """Expected output format from this tool. Override as needed."""
        return OutputFormat.RAW

    def normalize_output(self, output: str) -> str:
        """Normalize tool output to a standard format.

        Override to implement tool-specific normalization.
        Default strips ANSI codes and normalizes whitespace.

        Args:
            output: Raw output from the tool

        Returns:
            Normalized output string

        """
        return OutputNormalizer.normalize(output)

    def get_config_key(self) -> str:
        """Get the configuration key for this tool's settings."""
        return f"tool.{self.name}"

    def configure(self, config: dict[str, Any]) -> None:
        """Update provider configuration at runtime.

        Args:
            config: Configuration dict with keys like timeout, flags, etc.

        """
        self._config.update(config)

    def get_info(self) -> dict[str, Any]:
        """Get provider information for display/debugging."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "executable": self.executable,
            "input_method": self.input_method.value,
            "timeout": self.timeout,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "default_flags": self.default_flags,
            "available": self.is_available(),
            "capabilities": {
                "streaming": self.capabilities.supports_streaming,
                "conversation": self.capabilities.supports_conversation,
                "system_prompt": self.capabilities.supports_system_prompt,
                "tools": self.capabilities.supports_tools,
                "vision": self.capabilities.supports_vision,
                "max_context": self.capabilities.max_context_length,
            },
        }
