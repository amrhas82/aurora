"""AURORA Reasoning Package - LLM integration and reasoning logic."""

__version__ = "0.1.0"

from .llm_client import (
    AnthropicClient,
    LLMClient,
    LLMResponse,
    OpenAIClient,
    OllamaClient,
    extract_json_from_text,
)

__all__ = [
    "LLMClient",
    "LLMResponse",
    "AnthropicClient",
    "OpenAIClient",
    "OllamaClient",
    "extract_json_from_text",
]
