"""Agent Discovery module for AURORA CLI.

This module provides multi-source agent discovery, parsing, and manifest
management for AI coding assistant agents from various configuration
directories:

- ~/.claude/agents/ (Claude Code)
- ~/.config/ampcode/agents/ (AMP Code)
- ~/.config/droid/agent/ (Droid)
- ~/.config/opencode/agent/ (OpenCode)

Main Components:
    AgentScanner: Multi-source agent file discovery
    AgentParser: Frontmatter extraction with Pydantic validation
    ManifestManager: Manifest generation, caching, auto-refresh
    AgentInfo: Core agent metadata model
    AgentManifest: Manifest schema with indexes

Example:
    >>> from aurora_cli.agent_discovery import (
    ...     AgentScanner,
    ...     AgentParser,
    ...     ManifestManager,
    ...     AgentInfo,
    ...     AgentManifest,
    ... )
    >>>
    >>> # Quick start: get manifest with auto-refresh
    >>> manager = ManifestManager()
    >>> manifest = manager.get_or_refresh(Path("~/.aurora/cache/agent_manifest.json"))
    >>> print(f"Found {manifest.stats.total} agents")
    >>>
    >>> # Search for agents
    >>> agent = manifest.get_agent("qa-test-architect")
    >>> if agent:
    ...     print(f"Role: {agent.role}")
    ...     print(f"Goal: {agent.goal}")
"""

from aurora_cli.agent_discovery.manifest import ManifestManager, should_refresh_manifest
from aurora_cli.agent_discovery.models import AgentCategory, AgentInfo, AgentManifest, ManifestStats
from aurora_cli.agent_discovery.parser import AgentParser
from aurora_cli.agent_discovery.scanner import DEFAULT_DISCOVERY_PATHS, AgentScanner

__all__ = [
    # Scanner
    "AgentScanner",
    "DEFAULT_DISCOVERY_PATHS",
    # Parser
    "AgentParser",
    # Manifest
    "ManifestManager",
    "should_refresh_manifest",
    # Models
    "AgentCategory",
    "AgentInfo",
    "AgentManifest",
    "ManifestStats",
]
