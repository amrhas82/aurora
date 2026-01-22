"""Multi-source agent file discovery for AURORA CLI.

This module provides the AgentScanner class for discovering agent markdown files
from multiple standard directories used by various AI coding assistants.

The scanner uses the centralized tool paths registry (paths.py) for default
discovery paths, covering all 20 supported AI coding tools.

The scanner handles missing directories gracefully with logging, and yields
file paths for processing by the AgentParser.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator


logger = logging.getLogger(__name__)


def get_default_discovery_paths() -> list[str]:
    """Get default agent discovery paths from the tool registry.

    Returns:
        List of agent directory paths for all 20 supported tools

    """
    from aurora_cli.configurators.slash.paths import get_all_agent_paths

    return get_all_agent_paths()


# Supported agent file extensions
AGENT_FILE_EXTENSIONS: frozenset[str] = frozenset({".md", ".markdown"})


class AgentScanner:
    """Multi-source agent file scanner.

    Discovers agent markdown files from multiple configured directories,
    handling missing paths gracefully with logging.

    Attributes:
        discovery_paths: List of directories to scan for agent files

    Example:
        >>> scanner = AgentScanner()
        >>> for file_path in scanner.scan_all_sources():
        ...     print(f"Found agent: {file_path}")
        Found agent: /home/user/.claude/agents/quality-assurance.md
        Found agent: /home/user/.claude/agents/code-developer.md

        >>> # With custom paths
        >>> scanner = AgentScanner(["/custom/agents"])
        >>> sources = scanner.discover_sources()
        >>> print(sources)
        [Path('/custom/agents')]

    """

    def __init__(self, discovery_paths: list[str] | None = None) -> None:
        """Initialize the AgentScanner.

        Args:
            discovery_paths: Optional list of paths to scan. If not provided,
                           uses paths from the tool registry (all 20 tools).
                           Paths may contain tilde (~) for home directory expansion.

        """
        if discovery_paths is None:
            discovery_paths = get_default_discovery_paths()

        self._raw_paths = discovery_paths

    @property
    def discovery_paths(self) -> list[str]:
        """Get the raw discovery paths (before expansion).

        Returns:
            List of configured discovery paths

        """
        return self._raw_paths.copy()

    def discover_sources(self) -> list[Path]:
        """Return list of existing discovery paths from configuration.

        Expands tilde in paths and filters to only existing directories.
        Logs a debug message for each missing directory.

        Returns:
            List of Path objects for existing agent directories

        Example:
            >>> scanner = AgentScanner()
            >>> existing = scanner.discover_sources()
            >>> for path in existing:
            ...     print(f"Source: {path}")
            Source: /home/user/.claude/agents

        """
        existing_paths: list[Path] = []

        for raw_path in self._raw_paths:
            expanded_path = Path(raw_path).expanduser().resolve()

            if expanded_path.exists() and expanded_path.is_dir():
                existing_paths.append(expanded_path)
                logger.debug("Discovered agent source: %s", expanded_path)
            else:
                logger.debug("Agent source not found (skipping): %s", raw_path)

        return existing_paths

    def scan_directory(self, directory: Path) -> Iterator[Path]:
        """Scan a single directory for agent markdown files.

        Yields paths to all .md and .markdown files in the directory
        (non-recursive). Files are sorted alphabetically for consistent
        ordering.

        Args:
            directory: Directory path to scan

        Yields:
            Path objects for each agent file found

        Example:
            >>> scanner = AgentScanner()
            >>> agent_dir = Path("~/.claude/agents").expanduser()
            >>> for path in scanner.scan_directory(agent_dir):
            ...     print(path.name)
            code-developer.md
            orchestrator.md
            quality-assurance.md

        """
        if not directory.exists():
            logger.warning("Directory does not exist: %s", directory)
            return

        if not directory.is_dir():
            logger.warning("Path is not a directory: %s", directory)
            return

        try:
            # Get all files with agent extensions, sorted for consistent ordering
            agent_files = sorted(
                f
                for f in directory.iterdir()
                if f.is_file() and f.suffix.lower() in AGENT_FILE_EXTENSIONS
            )

            for file_path in agent_files:
                logger.debug("Found agent file: %s", file_path)
                yield file_path

        except PermissionError as e:
            logger.warning("Permission denied scanning directory %s: %s", directory, e)
        except OSError as e:
            logger.warning("Error scanning directory %s: %s", directory, e)

    def scan_all_sources(self) -> Iterator[Path]:
        """Scan all configured sources for agent files.

        Discovers existing source directories and yields paths to all
        agent markdown files found. Handles missing directories and
        permission errors gracefully with logging.

        Yields:
            Path objects for each agent file discovered across all sources

        Example:
            >>> scanner = AgentScanner()
            >>> all_agents = list(scanner.scan_all_sources())
            >>> print(f"Found {len(all_agents)} agent files")
            Found 12 agent files

        """
        sources = self.discover_sources()

        if not sources:
            logger.info(
                "No agent source directories found. Checked: %s",
                ", ".join(self._raw_paths),
            )
            return

        logger.info("Scanning %d agent source(s) for agent files", len(sources))

        for source_dir in sources:
            logger.debug("Scanning source: %s", source_dir)
            yield from self.scan_directory(source_dir)

    def get_source_stats(self) -> dict[str, int]:
        """Get statistics about agent files per source directory.

        Returns:
            Dictionary mapping source path to count of agent files found

        Example:
            >>> scanner = AgentScanner()
            >>> stats = scanner.get_source_stats()
            >>> for source, count in stats.items():
            ...     print(f"{source}: {count} agents")
            /home/user/.claude/agents: 8 agents
            /home/user/.config/ampcode/agents: 3 agents

        """
        stats: dict[str, int] = {}

        for source_dir in self.discover_sources():
            count = sum(1 for _ in self.scan_directory(source_dir))
            stats[str(source_dir)] = count

        return stats
