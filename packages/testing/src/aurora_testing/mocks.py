"""Mock implementations for AURORA testing.

Provides predictable mock implementations:
- MockLLM: Predictable LLM responses for testing
- MockAgent: Simulated agent for testing agent registry
- MockParser: Configurable parser for testing
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aurora_core.chunks.base import Chunk

# ============================================================================
# Mock LLM
# ============================================================================


@dataclass
class MockLLMResponse:
    """Mock LLM response structure.

    Attributes:
        content: Response content text.
        tokens_used: Number of tokens consumed.
        model: Model identifier.
        latency_ms: Simulated latency in milliseconds.

    """

    content: str
    tokens_used: int = 100
    model: str = "mock-model-1.0"
    latency_ms: int = 50


class MockLLM:
    """Mock LLM for predictable testing.

    Provides configurable responses for testing code that interacts
    with LLMs without making actual API calls.

    Examples:
        >>> # Simple fixed response
        >>> llm = MockLLM(default_response="Test response")
        >>> response = llm.complete("prompt")
        >>> assert response.content == "Test response"

        >>> # Response based on prompt content
        >>> llm = MockLLM()
        >>> llm.add_response_rule(
        ...     lambda prompt: "function" in prompt,
        ...     "Here is a function..."
        ... )
        >>> response = llm.complete("write a function")
        >>> assert "function" in response.content

        >>> # Simulate errors
        >>> llm = MockLLM()
        >>> llm.set_error_mode(exception=RuntimeError("API error"))
        >>> # llm.complete("prompt")  # Raises RuntimeError

    """

    def __init__(
        self,
        default_response: str = "Mock LLM response",
        default_tokens: int = 100,
        default_latency_ms: int = 50,
    ):
        """Initialize MockLLM.

        Args:
            default_response: Default response text.
            default_tokens: Default token count.
            default_latency_ms: Default simulated latency.

        """
        self.default_response = default_response
        self.default_tokens = default_tokens
        self.default_latency_ms = default_latency_ms

        # Response rules: (condition, response_generator)
        self.response_rules: list[tuple[Callable[[str], bool], Callable[[str], str]]] = []

        # Error simulation
        self.error_mode = False
        self.error_exception: Exception | None = None

        # Call tracking
        self.calls: list[dict[str, Any]] = []
        self.call_count = 0

    def add_response_rule(
        self,
        condition: Callable[[str], bool],
        response: str | Callable[[str], str],
    ) -> None:
        """Add a conditional response rule.

        Args:
            condition: Function that checks if rule applies to prompt.
            response: Fixed string or function that generates response.

        Examples:
            >>> llm = MockLLM()
            >>> llm.add_response_rule(
            ...     lambda p: "python" in p.lower(),
            ...     "Here is Python code..."
            ... )
            >>> llm.add_response_rule(
            ...     lambda p: len(p) > 100,
            ...     lambda p: f"Long prompt ({len(p)} chars)"
            ... )

        """
        response_func = (lambda _: response) if isinstance(response, str) else response

        self.response_rules.append((condition, response_func))

    def set_error_mode(self, exception: Exception) -> None:
        """Enable error mode to simulate failures.

        Args:
            exception: Exception to raise on complete() calls.

        """
        self.error_mode = True
        self.error_exception = exception

    def clear_error_mode(self) -> None:
        """Disable error mode."""
        self.error_mode = False
        self.error_exception = None

    def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **_kwargs: Any,
    ) -> MockLLMResponse:
        """Generate completion for prompt.

        Args:
            prompt: Input prompt text.
            temperature: Temperature parameter (ignored in mock).
            max_tokens: Maximum tokens (ignored in mock).
            **kwargs: Additional parameters (ignored in mock).

        Returns:
            MockLLMResponse: Mock response object.

        Raises:
            Exception: If error mode is enabled.

        """
        # Track call
        self.call_count += 1
        call_info = {
            "call_number": self.call_count,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timestamp": datetime.now(),
        }
        self.calls.append(call_info)

        # Simulate error if enabled
        if self.error_mode and self.error_exception:
            raise self.error_exception

        # Check response rules
        for condition, response_func in self.response_rules:
            if condition(prompt):
                return MockLLMResponse(
                    content=response_func(prompt),
                    tokens_used=self.default_tokens,
                    latency_ms=self.default_latency_ms,
                )

        # Default response
        return MockLLMResponse(
            content=self.default_response,
            tokens_used=self.default_tokens,
            latency_ms=self.default_latency_ms,
        )

    def reset(self) -> None:
        """Reset call tracking and clear rules."""
        self.calls.clear()
        self.call_count = 0
        self.response_rules.clear()
        self.clear_error_mode()

    def get_last_prompt(self) -> str | None:
        """Get the last prompt sent to the LLM.

        Returns:
            Last prompt string, or None if no calls made.

        """
        if self.calls:
            return str(self.calls[-1]["prompt"])
        return None

    def assert_called(self) -> None:
        """Assert that LLM was called at least once.

        Raises:
            AssertionError: If no calls were made.

        """
        assert self.call_count > 0, "MockLLM was not called"

    def assert_called_with(self, prompt_substring: str) -> None:
        """Assert that LLM was called with prompt containing substring.

        Args:
            prompt_substring: Expected substring in prompt.

        Raises:
            AssertionError: If substring not found in any prompt.

        """
        for call in self.calls:
            if prompt_substring in call["prompt"]:
                return
        raise AssertionError(f"MockLLM was not called with prompt containing '{prompt_substring}'")

    def assert_call_count(self, expected_count: int) -> None:
        """Assert specific number of calls.

        Args:
            expected_count: Expected number of calls.

        Raises:
            AssertionError: If call count doesn't match.

        """
        assert (
            self.call_count == expected_count
        ), f"Expected {expected_count} calls, got {self.call_count}"


# ============================================================================
# Mock Agent
# ============================================================================


@dataclass
class MockAgent:
    """Mock agent for testing agent registry and discovery.

    Attributes:
        agent_id: Unique agent identifier.
        name: Human-readable agent name.
        agent_type: Agent type (local, remote, mcp).
        capabilities: List of agent capabilities.
        domains: List of supported domains.
        is_available: Whether agent is currently available.
        execution_results: Predefined results for execute calls.

    """

    agent_id: str
    name: str
    agent_type: str = "local"
    capabilities: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    is_available: bool = True
    execution_results: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize call tracking."""
        self.calls: list[dict[str, Any]] = []

    def execute(self, task: str, context: dict[str, Any] | None = None) -> Any:
        """Execute a task (mock implementation).

        Args:
            task: Task description.
            context: Optional execution context.

        Returns:
            Predefined result or generic response.

        """
        call_info = {
            "task": task,
            "context": context,
            "timestamp": datetime.now(),
        }
        self.calls.append(call_info)

        # Return predefined result if available
        if task in self.execution_results:
            return self.execution_results[task]

        # Default mock result
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "task": task,
            "result": f"Mock execution result for: {task}",
        }

    def can_handle(self, capability: str, domain: str | None = None) -> bool:
        """Check if agent can handle capability/domain.

        Args:
            capability: Required capability.
            domain: Optional domain requirement.

        Returns:
            True if agent supports the capability and domain.

        """
        if capability not in self.capabilities:
            return False

        return not (domain and domain not in self.domains)


# ============================================================================
# Mock Parser
# ============================================================================


class MockParser:
    """Mock code parser for testing.

    Provides configurable parsing behavior without actual parsing.

    Examples:
        >>> parser = MockParser(language="python")
        >>> parser.set_parse_result([mock_chunk1, mock_chunk2])
        >>> chunks = parser.parse(Path("/test.py"))
        >>> assert len(chunks) == 2

    """

    def __init__(self, language: str = "mock") -> None:
        """Initialize MockParser.

        Args:
            language: Language identifier.

        """
        self.language = language
        self.parse_results: dict[str, list[Chunk]] = {}
        self.default_result: list[Chunk] = []
        self.should_fail = False
        self.failure_exception: Exception | None = None
        self.calls: list[Path] = []

    def can_parse(self, file_path: Path) -> bool:
        """Check if parser can handle file.

        Args:
            file_path: Path to file.

        Returns:
            True if file extension matches language.

        """
        # Mock parser accepts files matching its language
        if self.language == "python":
            return str(file_path).endswith((".py", ".pyi"))
        if self.language == "mock":
            return str(file_path).endswith(".mock")
        return False

    def parse(self, file_path: Path) -> list[Chunk]:
        """Parse file and return chunks.

        Args:
            file_path: Absolute path to file.

        Returns:
            List of chunks (configured or default).

        Raises:
            Exception: If failure mode is enabled.

        """
        self.calls.append(file_path)

        if self.should_fail and self.failure_exception:
            raise self.failure_exception

        # Return specific result for this file if configured
        file_key = str(file_path)
        if file_key in self.parse_results:
            return self.parse_results[file_key]

        # Return default result
        return self.default_result.copy()

    def set_parse_result(
        self,
        chunks: list[Chunk],
        file_path: Path | None = None,
    ) -> None:
        """Set parsing result for file.

        Args:
            chunks: List of chunks to return.
            file_path: Specific file path, or None for default.

        """
        if file_path:
            self.parse_results[str(file_path)] = chunks
        else:
            self.default_result = chunks

    def set_failure_mode(self, exception: Exception) -> None:
        """Enable failure mode.

        Args:
            exception: Exception to raise on parse.

        """
        self.should_fail = True
        self.failure_exception = exception

    def clear_failure_mode(self) -> None:
        """Disable failure mode."""
        self.should_fail = False
        self.failure_exception = None

    def reset(self) -> None:
        """Reset parser state."""
        self.parse_results.clear()
        self.default_result = []
        self.calls.clear()
        self.clear_failure_mode()


# ============================================================================
# Mock Store
# ============================================================================


class MockStore:
    """Mock storage backend for testing.

    Provides configurable store behavior without actual persistence.
    Useful for testing error handling and edge cases.
    """

    def __init__(self) -> None:
        """Initialize MockStore."""
        self.chunks: dict[str, Chunk] = {}
        self.save_should_fail = False
        self.retrieve_should_fail = False
        self.failure_exception: Exception | None = None
        self.save_calls: list[str] = []
        self.retrieve_calls: list[str] = []

    def save_chunk(self, chunk: Chunk) -> None:
        """Save chunk to mock store.

        Args:
            chunk: Chunk to save.

        Raises:
            Exception: If failure mode is enabled.

        """
        self.save_calls.append(chunk.id)

        if self.save_should_fail and self.failure_exception:
            raise self.failure_exception

        self.chunks[chunk.id] = chunk

    def retrieve_chunk(self, chunk_id: str) -> Chunk | None:
        """Retrieve chunk by ID.

        Args:
            chunk_id: Chunk identifier.

        Returns:
            Chunk if found, None otherwise.

        Raises:
            Exception: If failure mode is enabled.

        """
        self.retrieve_calls.append(chunk_id)

        if self.retrieve_should_fail and self.failure_exception:
            raise self.failure_exception

        return self.chunks.get(chunk_id)

    def list_chunks(self) -> list[str]:
        """List all chunk IDs.

        Returns:
            List of chunk IDs.

        """
        return list(self.chunks.keys())

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete chunk by ID.

        Args:
            chunk_id: Chunk identifier.

        Returns:
            True if deleted, False if not found.

        """
        if chunk_id in self.chunks:
            del self.chunks[chunk_id]
            return True
        return False

    def set_save_failure(self, exception: Exception) -> None:
        """Enable save failure mode.

        Args:
            exception: Exception to raise on save.

        """
        self.save_should_fail = True
        self.failure_exception = exception

    def set_retrieve_failure(self, exception: Exception) -> None:
        """Enable retrieve failure mode.

        Args:
            exception: Exception to raise on retrieve.

        """
        self.retrieve_should_fail = True
        self.failure_exception = exception

    def clear_failure_modes(self) -> None:
        """Disable all failure modes."""
        self.save_should_fail = False
        self.retrieve_should_fail = False
        self.failure_exception = None

    def reset(self) -> None:
        """Reset store state."""
        self.chunks.clear()
        self.save_calls.clear()
        self.retrieve_calls.clear()
        self.clear_failure_modes()
