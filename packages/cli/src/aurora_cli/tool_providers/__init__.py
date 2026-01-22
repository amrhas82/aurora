"""Tool providers for headless execution.

This module implements a factory pattern for dynamic tool instantiation,
allowing the headless command to work with multiple AI tools (Claude, OpenCode, etc.)
simultaneously or in sequence.

Key Components:
- ToolProvider: Abstract base class for all tool providers
- ToolProviderRegistry: Singleton registry with factory pattern and auto-discovery
- GenericToolProvider: Config-driven provider for adding tools without code
- Built-in providers: Claude, OpenCode, Cursor, Gemini, Codex

Usage:
    # Get registry singleton
    registry = ToolProviderRegistry.get_instance()

    # Get a provider by name
    claude = registry.get("claude")

    # Run multiple tools in parallel
    providers = registry.get_multiple(["claude", "opencode"])

    # Add custom tool via config
    registry.register_from_config("mytool", {
        "executable": "mytool",
        "input_method": "stdin",
        "flags": ["--ai-mode"],
    })

    # Configure existing provider
    registry.configure("claude", {"timeout": 300})
"""

from aurora_cli.tool_providers.base import (
    CapabilityRouter,
    InputMethod,
    OutputFormat,
    OutputNormalizer,
    ToolAdapter,
    ToolCapabilities,
    ToolProvider,
    ToolResult,
    ToolStatus,
)
from aurora_cli.tool_providers.claude import ClaudeToolProvider
from aurora_cli.tool_providers.codex import CodexToolProvider
from aurora_cli.tool_providers.cursor import CursorToolProvider
from aurora_cli.tool_providers.gemini import GeminiToolProvider
from aurora_cli.tool_providers.generic import GenericToolProvider
from aurora_cli.tool_providers.opencode import OpenCodeToolProvider
from aurora_cli.tool_providers.output_handler import (
    ClaudeOutputHandler,
    CodeBlock,
    FileChange,
    OpenCodeOutputHandler,
    OutputHandler,
    ParsedOutput,
    ParsedStatus,
    ToolCommand,
    get_handler,
)
from aurora_cli.tool_providers.registry import ToolProviderRegistry


__all__ = [
    # Base classes
    "ToolProvider",
    "ToolAdapter",
    "ToolResult",
    "ToolStatus",
    "ToolCapabilities",
    "InputMethod",
    "OutputFormat",
    # Utilities
    "OutputNormalizer",
    "CapabilityRouter",
    # Output handling
    "OutputHandler",
    "ClaudeOutputHandler",
    "OpenCodeOutputHandler",
    "ParsedOutput",
    "ParsedStatus",
    "CodeBlock",
    "FileChange",
    "ToolCommand",
    "get_handler",
    # Registry
    "ToolProviderRegistry",
    # Providers
    "ClaudeToolProvider",
    "OpenCodeToolProvider",
    "CursorToolProvider",
    "GeminiToolProvider",
    "CodexToolProvider",
    "GenericToolProvider",
]
