"""Agent manifest generation, caching, and auto-refresh for AURORA CLI.

This module provides the ManifestManager class for:
- Generating agent manifests from discovered agent files
- De-duplicating agents by ID with conflict warnings
- Building category indexes and statistics
- Saving/loading manifests with atomic writes
- Auto-refresh based on configurable intervals

The manifest provides efficient O(1) lookups by agent ID and category-based
filtering, enabling fast agent discovery CLI commands.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from aurora_cli.agent_discovery.models import AgentCategory, AgentManifest, ManifestStats
from aurora_cli.agent_discovery.parser import AgentParser
from aurora_cli.agent_discovery.scanner import AgentScanner


if TYPE_CHECKING:
    from aurora_cli.config import Config

logger = logging.getLogger(__name__)


class ManifestManager:
    """Manager for agent manifest generation, caching, and retrieval.

    Handles the full lifecycle of agent manifests:
    - Discovery and parsing of agent files from multiple sources
    - De-duplication with conflict warnings
    - Manifest generation with statistics
    - Atomic file operations for safe caching
    - Auto-refresh based on staleness

    Attributes:
        scanner: AgentScanner instance for file discovery
        parser: AgentParser instance for frontmatter parsing

    Example:
        >>> manager = ManifestManager()
        >>> manifest = manager.generate()
        >>> print(f"Found {manifest.stats.total} agents")
        Found 12 agents

        >>> # Save and load manifest
        >>> manager.save(manifest, Path("~/.aurora/cache/agent_manifest.json"))
        >>> loaded = manager.load(Path("~/.aurora/cache/agent_manifest.json"))

    """

    def __init__(
        self,
        scanner: AgentScanner | None = None,
        parser: AgentParser | None = None,
    ) -> None:
        """Initialize the ManifestManager.

        Args:
            scanner: Optional AgentScanner instance (creates default if not provided)
            parser: Optional AgentParser instance (creates default if not provided)

        """
        self.scanner = scanner or AgentScanner()
        self.parser = parser or AgentParser()

    def generate(self, sources: list[str] | None = None) -> AgentManifest:
        """Generate a new agent manifest from all sources.

        Scans configured directories for agent files, parses frontmatter,
        validates metadata, and builds an aggregated manifest with:
        - De-duplicated agents (warns on ID conflicts)
        - Category indexes for filtering
        - Statistics (total, by_category, malformed_files)

        Args:
            sources: Optional list of source paths to scan (uses scanner defaults if not provided)

        Returns:
            AgentManifest with discovered and validated agents

        Example:
            >>> manager = ManifestManager()
            >>> manifest = manager.generate()
            >>> print(f"Categories: {list(manifest.stats.by_category.keys())}")
            Categories: ['eng', 'qa', 'product', 'general']

        """
        # Create scanner with custom sources if provided
        if sources:
            scanner = AgentScanner(sources)
        else:
            scanner = self.scanner

        # Initialize manifest
        manifest = AgentManifest(
            generated_at=datetime.now().astimezone(),
            sources=[str(s) for s in scanner.discover_sources()],
            agents=[],
            stats=ManifestStats(),
        )

        # Track statistics
        total_parsed = 0
        malformed_count = 0
        category_counts: dict[str, int] = {cat.value: 0 for cat in AgentCategory}
        seen_ids: dict[str, str] = {}  # id -> source_file for conflict detection
        duplicates: list[str] = []  # collect duplicate IDs for single warning

        # Scan and parse all agent files
        for file_path in scanner.scan_all_sources():
            agent = self.parser.parse_file(file_path)

            if agent is None:
                malformed_count += 1
                continue

            total_parsed += 1

            # Check for duplicate IDs (collect for single warning)
            if agent.id in seen_ids:
                duplicates.append(agent.id)
                continue

            # Add to manifest
            manifest.add_agent(agent)
            seen_ids[agent.id] = str(file_path)
            category_counts[agent.category.value] += 1

        # Show info message for duplicates (expected when scanning multiple tools)
        if duplicates:
            unique_dups = sorted(set(duplicates))
            logger.info(
                "Found %d agents shared across tools (deduplicated): %s",
                len(duplicates),
                ", ".join(unique_dups[:5]) + ("..." if len(unique_dups) > 5 else ""),
            )

        # Update statistics
        manifest.stats = ManifestStats(
            total=len(manifest.agents),
            by_category=category_counts,
            malformed_files=malformed_count,
        )

        logger.info(
            "Generated manifest: %d agents from %d sources (%d duplicates skipped)",
            manifest.stats.total,
            len(manifest.sources),
            len(duplicates),
        )

        return manifest

    def save(self, manifest: AgentManifest, path: Path) -> None:
        """Save manifest to file with atomic write.

        Uses a temporary file and rename for atomic operation, ensuring
        the manifest file is never in a partially-written state.

        Args:
            manifest: AgentManifest to save
            path: Target file path

        Raises:
            OSError: If file cannot be written

        Example:
            >>> manager = ManifestManager()
            >>> manifest = manager.generate()
            >>> manager.save(manifest, Path("~/.aurora/cache/agent_manifest.json"))

        """
        resolved_path = Path(path).expanduser().resolve()

        # Ensure parent directory exists
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize manifest
        json_data = manifest.to_json_dict()

        # Atomic write: temp file + rename
        try:
            # Create temp file in same directory for atomic rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                dir=resolved_path.parent,
                delete=False,
            ) as tmp_file:
                json.dump(json_data, tmp_file, indent=2, default=str)
                tmp_path = Path(tmp_file.name)

            # Atomic rename
            tmp_path.rename(resolved_path)

            logger.info("Saved manifest to %s", resolved_path)

        except Exception as e:
            # Clean up temp file on error
            if "tmp_path" in locals() and tmp_path.exists():
                tmp_path.unlink()
            logger.error("Failed to save manifest to %s: %s", path, e)
            raise

    def load(self, path: Path) -> AgentManifest | None:
        """Load manifest from file.

        Args:
            path: Path to manifest JSON file

        Returns:
            AgentManifest if successfully loaded, None if file doesn't exist
            or is invalid

        Example:
            >>> manager = ManifestManager()
            >>> manifest = manager.load(Path("~/.aurora/cache/agent_manifest.json"))
            >>> if manifest:
            ...     print(f"Loaded {manifest.stats.total} agents")

        """
        resolved_path = Path(path).expanduser().resolve()

        if not resolved_path.exists():
            logger.debug("Manifest file not found: %s", path)
            return None

        try:
            with open(resolved_path) as f:
                data = json.load(f)

            manifest = AgentManifest.from_json_dict(data)
            logger.debug(
                "Loaded manifest from %s (%d agents)",
                path,
                manifest.stats.total,
            )
            return manifest

        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in manifest file %s: %s", path, e)
            return None
        except Exception as e:
            logger.warning("Failed to load manifest from %s: %s", path, e)
            return None

    def should_refresh(self, path: Path, refresh_interval_hours: int = 24) -> bool:
        """Check if manifest should be refreshed based on staleness.

        A manifest should be refreshed if:
        - The manifest file doesn't exist
        - The manifest is older than refresh_interval_hours

        Args:
            path: Path to manifest file
            refresh_interval_hours: Hours before manifest is considered stale (default: 24)

        Returns:
            True if manifest should be refreshed, False otherwise

        Example:
            >>> manager = ManifestManager()
            >>> if manager.should_refresh(Path("manifest.json"), refresh_interval_hours=24):
            ...     manifest = manager.generate()
            ...     manager.save(manifest, Path("manifest.json"))

        """
        resolved_path = Path(path).expanduser().resolve()

        # Refresh if file doesn't exist
        if not resolved_path.exists():
            logger.debug("Manifest does not exist at %s - refresh needed", path)
            return True

        # Check file age
        try:
            mtime = datetime.fromtimestamp(resolved_path.stat().st_mtime)
            age = datetime.now() - mtime
            max_age = timedelta(hours=refresh_interval_hours)

            if age >= max_age:
                logger.debug(
                    "Manifest at %s is %s old (max: %s) - refresh needed",
                    path,
                    age,
                    max_age,
                )
                return True

            logger.debug(
                "Manifest at %s is %s old (max: %s) - no refresh needed",
                path,
                age,
                max_age,
            )
            return False

        except OSError as e:
            logger.warning("Cannot check manifest age at %s: %s - refresh needed", path, e)
            return True

    def get_or_refresh(
        self,
        path: Path,
        auto_refresh: bool = True,
        refresh_interval_hours: int = 24,
    ) -> AgentManifest:
        """Get manifest from cache, refreshing if stale.

        This is the primary method for consumers - it handles caching
        transparently, only regenerating when necessary.

        Args:
            path: Path to cached manifest file
            auto_refresh: Whether to check staleness and refresh (default: True)
            refresh_interval_hours: Hours before considering stale (default: 24)

        Returns:
            AgentManifest (either loaded from cache or freshly generated)

        Example:
            >>> manager = ManifestManager()
            >>> manifest = manager.get_or_refresh(
            ...     Path("~/.aurora/cache/agent_manifest.json"),
            ...     auto_refresh=True,
            ...     refresh_interval_hours=24
            ... )
            >>> print(f"Got {manifest.stats.total} agents")

        """
        # Check if we should refresh
        needs_refresh = auto_refresh and self.should_refresh(path, refresh_interval_hours)

        # Try to load existing manifest
        if not needs_refresh:
            manifest = self.load(path)
            if manifest is not None:
                return manifest
            # Manifest file exists but couldn't be loaded - refresh
            logger.info("Manifest corrupted or invalid - regenerating")

        # Generate fresh manifest
        manifest = self.generate()
        self.save(manifest, path)
        return manifest


def should_refresh_manifest(manifest_path: Path, config: Config) -> bool:
    """Check if manifest should be refreshed based on config settings.

    Convenience function that uses config values for auto_refresh and
    refresh_interval settings.

    Args:
        manifest_path: Path to manifest file
        config: Config object with agents settings

    Returns:
        True if manifest should be refreshed, False otherwise

    Example:
        >>> from aurora_cli.config import load_config
        >>> config = load_config()
        >>> if should_refresh_manifest(Path("manifest.json"), config):
        ...     # Perform refresh
        ...     pass

    """
    # Check if auto_refresh is enabled
    auto_refresh = getattr(config, "agents_auto_refresh", True)
    if not auto_refresh:
        # Auto-refresh disabled, only refresh if file doesn't exist
        resolved_path = Path(manifest_path).expanduser().resolve()
        return not resolved_path.exists()

    # Get refresh interval
    refresh_interval = getattr(config, "agents_refresh_interval_hours", 24)

    # Use ManifestManager to check
    manager = ManifestManager()
    return manager.should_refresh(manifest_path, refresh_interval)
