"""AURORA Reasoning Package - LLM integration and reasoning logic."""

__version__ = "0.1.0"

from .llm_client import (
    AnthropicClient,
    LLMClient,
    LLMResponse,
    OllamaClient,
    OpenAIClient,
    extract_json_from_text,
)
from .synthesize import SynthesisResult, synthesize_results, verify_synthesis


__all__ = [
    "LLMClient",
    "LLMResponse",
    "AnthropicClient",
    "OpenAIClient",
    "OllamaClient",
    "extract_json_from_text",
    "SynthesisResult",
    "synthesize_results",
    "verify_synthesis",
]
