"""CLI LLM client implementations.

This package provides LLM client implementations that pipe to external CLI tools
instead of making API calls.
"""

from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient


__all__ = ["CLIPipeLLMClient"]
