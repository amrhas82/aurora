"""Abstract LLM client interface and implementations for AURORA reasoning."""

import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any, cast

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class LLMResponse(BaseModel):
    """Response from an LLM generation call."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    metadata: dict[str, Any] = {}


class LLMClient(ABC):
    """Abstract interface for LLM clients.

    Provides a consistent interface across different LLM providers
    (Anthropic, OpenAI, Ollama, etc.) for text generation and JSON-structured output.

    Implementations must handle:
    - API authentication
    - Rate limiting
    - Error handling and retries
    - Token counting
    - Cost tracking
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion from prompt.

        Args:
            prompt: The user prompt/question
            model: Optional model override (uses default if not specified)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            system: Optional system prompt
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ValueError: If prompt is empty or invalid
            RuntimeError: If API call fails after retries

        """

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON-structured output from prompt.

        This method enforces JSON-only output, extracting valid JSON even if
        the LLM wraps it in markdown code blocks or adds extra text.

        Args:
            prompt: The user prompt/question (should request JSON output)
            model: Optional model override (uses default if not specified)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            system: Optional system prompt
            **kwargs: Provider-specific parameters

        Returns:
            Parsed JSON object as Python dict

        Raises:
            ValueError: If prompt is empty, invalid, or output is not valid JSON
            RuntimeError: If API call fails after retries

        """

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        """

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Get the default model identifier for this client."""


def extract_json_from_text(text: str) -> dict[str, Any]:
    """Extract JSON from text that may contain markdown code blocks or extra text.

    Args:
        text: Text potentially containing JSON

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If no valid JSON found

    """
    # Try direct parse first
    try:
        result: dict[str, Any] = json.loads(text)
        return result
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    for match in matches:
        try:
            result_match: dict[str, Any] = json.loads(match)
            return result_match
        except json.JSONDecodeError:
            continue

    # Try finding JSON object anywhere in text
    json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_object_pattern, text, re.DOTALL)
    for match in matches:
        try:
            result_obj: dict[str, Any] = json.loads(match)
            return result_obj
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON found in text: {text[:200]}...")


class AnthropicClient(LLMClient):
    """Anthropic Claude client implementation.

    Features:
    - Claude Sonnet/Opus model support
    - Automatic retry with exponential backoff
    - Rate limiting handling
    - Token counting and cost tracking hooks
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-sonnet-4-20250514",
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            default_model: Default model to use

        Raises:
            ValueError: If no API key provided

        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter.",
            )

        self._default_model = default_model
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests for rate limiting

        # Lazy import to avoid requiring anthropic if not used
        try:
            import anthropic

            self._anthropic = anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        except ImportError as e:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic",
            ) from e

    def _rate_limit(self) -> None:
        """Enforce minimum time between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion from prompt.

        Args:
            prompt: The user prompt/question
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional Anthropic API parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If API call fails after retries

        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        self._rate_limit()

        try:
            response = self._client.messages.create(
                model=model or self._default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason or "unknown",
                metadata={
                    "id": response.id,
                    "stop_sequence": response.stop_sequence,
                },
            )
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}") from e

    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON-structured output from prompt.

        Args:
            prompt: The user prompt/question (should request JSON output)
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional Anthropic API parameters

        Returns:
            Parsed JSON object

        Raises:
            ValueError: If prompt is empty or output is not valid JSON
            RuntimeError: If API call fails after retries

        """
        # Enhance system prompt to enforce JSON output
        json_system = (
            (system or "")
            + "\n\nYou MUST respond with valid JSON only. Do not include markdown code blocks, explanations, or any text outside the JSON object."
        )

        response = self.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=json_system.strip(),
            **kwargs,
        )

        try:
            return extract_json_from_text(response.content)
        except ValueError as e:
            raise ValueError(f"Failed to extract JSON from response: {e}") from e

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses approximate heuristic: 1 token ≈ 4 characters for English text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        """
        # Anthropic doesn't provide a public tokenizer, use heuristic
        return len(text) // 4

    @property
    def default_model(self) -> str:
        """Get the default model identifier."""
        return self._default_model


class OpenAIClient(LLMClient):
    """OpenAI GPT client implementation.

    Features:
    - GPT-4/GPT-3.5 model support
    - Automatic retry with exponential backoff
    - Rate limiting handling
    - Token counting and cost tracking hooks
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gpt-4-turbo-preview",
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            default_model: Default model to use

        Raises:
            ValueError: If no API key provided

        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter.",
            )

        self._default_model = default_model
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests for rate limiting

        # Lazy import to avoid requiring openai if not used
        try:
            import openai

            self._openai = openai
            self._client = openai.OpenAI(api_key=self._api_key)
        except ImportError as e:
            raise ImportError("openai package required. Install with: pip install openai") from e

    def _rate_limit(self) -> None:
        """Enforce minimum time between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion from prompt.

        Args:
            prompt: The user prompt/question
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional OpenAI API parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If API call fails after retries

        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        self._rate_limit()

        try:
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=model or self._default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=cast(Any, messages),  # OpenAI SDK expects specific message types
                **kwargs,
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "unknown",
                metadata={
                    "id": response.id,
                    "created": response.created,
                },
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON-structured output from prompt.

        Args:
            prompt: The user prompt/question (should request JSON output)
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional OpenAI API parameters

        Returns:
            Parsed JSON object

        Raises:
            ValueError: If prompt is empty or output is not valid JSON
            RuntimeError: If API call fails after retries

        """
        # Enhance system prompt to enforce JSON output
        json_system = (
            (system or "")
            + "\n\nYou MUST respond with valid JSON only. Do not include markdown code blocks, explanations, or any text outside the JSON object."
        )

        # OpenAI supports response_format for JSON mode
        if "response_format" not in kwargs:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=json_system.strip(),
            **kwargs,
        )

        try:
            return extract_json_from_text(response.content)
        except ValueError as e:
            raise ValueError(f"Failed to extract JSON from response: {e}") from e

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses approximate heuristic: 1 token ≈ 4 characters for English text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        """
        # OpenAI has tiktoken but it's an extra dependency, use heuristic
        return len(text) // 4

    @property
    def default_model(self) -> str:
        """Get the default model identifier."""
        return self._default_model


class OllamaClient(LLMClient):
    """Ollama local model client implementation.

    Features:
    - Local model support (llama2, mistral, etc.)
    - Configurable endpoint
    - Automatic retry with exponential backoff
    - No API key required
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        default_model: str = "llama2",
    ):
        """Initialize Ollama client.

        Args:
            endpoint: Ollama server endpoint
            default_model: Default model to use

        """
        self._endpoint = endpoint
        self._default_model = default_model
        self._last_request_time = 0.0
        self._min_request_interval = 0.05  # 50ms between requests for local models

        # Lazy import to avoid requiring ollama if not used
        try:
            import ollama

            self._ollama = ollama
            self._client = ollama.Client(host=endpoint)
        except ImportError as e:
            raise ImportError("ollama package required. Install with: pip install ollama") from e

    def _rate_limit(self) -> None:
        """Enforce minimum time between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=0.4),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion from prompt.

        Args:
            prompt: The user prompt/question
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional Ollama API parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If API call fails after retries

        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        self._rate_limit()

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat(
                model=model or self._default_model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    **kwargs.get("options", {}),
                },
            )

            # Ollama response structure
            content = response.get("message", {}).get("content", "")
            model_used = response.get("model", self._default_model)

            # Estimate tokens (Ollama doesn't always provide this)
            input_tokens = self.count_tokens(prompt + (system or ""))
            output_tokens = self.count_tokens(content)

            return LLMResponse(
                content=content,
                model=model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=response.get("done_reason", "stop"),
                metadata={
                    "total_duration": response.get("total_duration"),
                    "load_duration": response.get("load_duration"),
                    "prompt_eval_count": response.get("prompt_eval_count"),
                    "eval_count": response.get("eval_count"),
                },
            )
        except Exception as e:
            raise RuntimeError(f"Ollama API call failed: {e}") from e

    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON-structured output from prompt.

        Args:
            prompt: The user prompt/question (should request JSON output)
            model: Optional model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional Ollama API parameters

        Returns:
            Parsed JSON object

        Raises:
            ValueError: If prompt is empty or output is not valid JSON
            RuntimeError: If API call fails after retries

        """
        # Enhance system prompt to enforce JSON output
        json_system = (
            (system or "")
            + "\n\nYou MUST respond with valid JSON only. Do not include markdown code blocks, explanations, or any text outside the JSON object."
        )

        response = self.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=json_system.strip(),
            **kwargs,
        )

        try:
            return extract_json_from_text(response.content)
        except ValueError as e:
            raise ValueError(f"Failed to extract JSON from response: {e}") from e

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses approximate heuristic: 1 token ≈ 4 characters for English text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count

        """
        # Ollama doesn't provide a public tokenizer, use heuristic
        return len(text) // 4

    @property
    def default_model(self) -> str:
        """Get the default model identifier."""
        return self._default_model
