"""Slash command configurators for AI coding tools.

This module provides configurators for creating slash commands in various
AI coding tools (Claude Code, OpenCode, etc.) for Aurora CLI integration.

All 20 supported AI coding tools have dedicated configurators that can be
accessed via SlashCommandRegistry or imported directly.
"""

# Import all 20 configurator classes
from aurora_cli.configurators.slash.amazon_q import AmazonQSlashCommandConfigurator
from aurora_cli.configurators.slash.antigravity import AntigravitySlashCommandConfigurator
from aurora_cli.configurators.slash.auggie import AuggieSlashCommandConfigurator
from aurora_cli.configurators.slash.base import (
    ALL_COMMANDS,
    AURORA_MARKERS,
    SlashCommandConfigurator,
    SlashCommandTarget,
)
from aurora_cli.configurators.slash.claude import ClaudeSlashCommandConfigurator
from aurora_cli.configurators.slash.cline import ClineSlashCommandConfigurator
from aurora_cli.configurators.slash.codebuddy import CodeBuddySlashCommandConfigurator
from aurora_cli.configurators.slash.codex import CodexSlashCommandConfigurator
from aurora_cli.configurators.slash.costrict import CostrictSlashCommandConfigurator
from aurora_cli.configurators.slash.crush import CrushSlashCommandConfigurator
from aurora_cli.configurators.slash.cursor import CursorSlashCommandConfigurator
from aurora_cli.configurators.slash.factory import FactorySlashCommandConfigurator
from aurora_cli.configurators.slash.gemini import GeminiSlashCommandConfigurator
from aurora_cli.configurators.slash.github_copilot import GitHubCopilotSlashCommandConfigurator
from aurora_cli.configurators.slash.iflow import IflowSlashCommandConfigurator
from aurora_cli.configurators.slash.kilocode import KiloCodeSlashCommandConfigurator
from aurora_cli.configurators.slash.opencode import OpenCodeSlashCommandConfigurator
from aurora_cli.configurators.slash.qoder import QoderSlashCommandConfigurator
from aurora_cli.configurators.slash.qwen import QwenSlashCommandConfigurator
from aurora_cli.configurators.slash.registry import SlashCommandRegistry
from aurora_cli.configurators.slash.roocode import RooCodeSlashCommandConfigurator
from aurora_cli.configurators.slash.toml_base import TomlSlashCommandConfigurator
from aurora_cli.configurators.slash.windsurf import WindsurfSlashCommandConfigurator


__all__ = [
    # Base classes and constants
    "ALL_COMMANDS",
    "AURORA_MARKERS",
    "SlashCommandConfigurator",
    "SlashCommandRegistry",
    "SlashCommandTarget",
    "TomlSlashCommandConfigurator",
    # All 20 configurator classes (alphabetical)
    "AmazonQSlashCommandConfigurator",
    "AntigravitySlashCommandConfigurator",
    "AuggieSlashCommandConfigurator",
    "ClaudeSlashCommandConfigurator",
    "ClineSlashCommandConfigurator",
    "CodeBuddySlashCommandConfigurator",
    "CodexSlashCommandConfigurator",
    "CostrictSlashCommandConfigurator",
    "CrushSlashCommandConfigurator",
    "CursorSlashCommandConfigurator",
    "FactorySlashCommandConfigurator",
    "GeminiSlashCommandConfigurator",
    "GitHubCopilotSlashCommandConfigurator",
    "IflowSlashCommandConfigurator",
    "KiloCodeSlashCommandConfigurator",
    "OpenCodeSlashCommandConfigurator",
    "QoderSlashCommandConfigurator",
    "QwenSlashCommandConfigurator",
    "RooCodeSlashCommandConfigurator",
    "WindsurfSlashCommandConfigurator",
]
