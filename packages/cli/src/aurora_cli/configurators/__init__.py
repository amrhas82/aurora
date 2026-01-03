"""Tool configurators for Aurora initialization.

This module provides configurator classes for various AI coding tools
to enable OpenSpec-style AGENTS.md integration with Aurora planning.
"""

from .base import ToolConfigurator
from .registry import ToolRegistry, TOOL_OPTIONS
from .claude import ClaudeConfigurator
from .opencode import OpenCodeConfigurator
from .ampcode import AmpCodeConfigurator
from .droid import DroidConfigurator
from .agents import AgentsStandardConfigurator

__all__ = [
    "ToolConfigurator",
    "ToolRegistry",
    "TOOL_OPTIONS",
    "ClaudeConfigurator",
    "OpenCodeConfigurator",
    "AmpCodeConfigurator",
    "DroidConfigurator",
    "AgentsStandardConfigurator",
]
