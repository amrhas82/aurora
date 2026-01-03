"""Slash command configurators for AI coding tools.

This module provides configurators for creating slash commands in various
AI coding tools (Claude Code, OpenCode, etc.) for Aurora CLI integration.
"""

from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.registry import SlashCommandRegistry
from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator

__all__ = [
    "ALL_COMMANDS",
    "AURORA_MARKERS",
    "SlashCommandConfigurator",
    "SlashCommandRegistry",
    "SlashCommandTarget",
    "TomlSlashCommandConfigurator",
]
