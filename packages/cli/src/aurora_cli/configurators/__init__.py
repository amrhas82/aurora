"""Tool configurators for Aurora initialization.

This module provides configurator classes for various AI coding tools
to enable Aurora planning integration with AGENTS.md-style instructions.
"""

from .agents import AgentsStandardConfigurator
from .ampcode import AmpCodeConfigurator
from .base import ToolConfigurator
from .claude import ClaudeConfigurator
from .claude_commands import ClaudeCommandsConfigurator
from .droid import DroidConfigurator
from .opencode import OpenCodeConfigurator
from .registry import TOOL_OPTIONS, ToolRegistry


__all__ = [
    "AgentsStandardConfigurator",
    "AmpCodeConfigurator",
    "ClaudeCommandsConfigurator",
    "ClaudeConfigurator",
    "DroidConfigurator",
    "OpenCodeConfigurator",
    "TOOL_OPTIONS",
    "ToolConfigurator",
    "ToolRegistry",
]
