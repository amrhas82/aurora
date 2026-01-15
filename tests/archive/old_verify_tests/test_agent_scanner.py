"""Unit tests for AgentScanner module.

Tests multi-source agent file discovery with graceful handling
of missing directories and various file patterns.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from aurora_cli.agent_discovery.scanner import (
    AGENT_FILE_EXTENSIONS,
    DEFAULT_DISCOVERY_PATHS,
    AgentScanner,
)


class TestAgentScannerInit:
    """Tests for AgentScanner initialization."""

    def test_default_paths(self) -> None:
        """Scanner uses default paths when none provided."""
        scanner = AgentScanner()
        assert scanner.discovery_paths == DEFAULT_DISCOVERY_PATHS

    def test_custom_paths(self) -> None:
        """Scanner accepts custom discovery paths."""
        custom_paths = ["/custom/path1", "/custom/path2"]
        scanner = AgentScanner(custom_paths)
        assert scanner.discovery_paths == custom_paths

    def test_empty_paths(self) -> None:
        """Scanner handles empty path list."""
        scanner = AgentScanner([])
        assert scanner.discovery_paths == []
        assert list(scanner.scan_all_sources()) == []


class TestAgentScannerDiscoverSources:
    """Tests for discover_sources method."""

    def test_discover_existing_directory(self, tmp_path: Path) -> None:
        """Discovers existing directories."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        scanner = AgentScanner([str(agent_dir)])
        sources = scanner.discover_sources()

        assert len(sources) == 1
        assert sources[0] == agent_dir

    def test_skip_missing_directories(self, tmp_path: Path) -> None:
        """Skips directories that don't exist."""
        existing_dir = tmp_path / "exists"
        existing_dir.mkdir()
        missing_dir = tmp_path / "missing"

        scanner = AgentScanner([str(existing_dir), str(missing_dir)])
        sources = scanner.discover_sources()

        assert len(sources) == 1
        assert sources[0] == existing_dir

    def test_skip_files_not_directories(self, tmp_path: Path) -> None:
        """Skips paths that are files, not directories."""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("I'm a file")

        scanner = AgentScanner([str(file_path)])
        sources = scanner.discover_sources()

        assert len(sources) == 0

    def test_expand_tilde(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Expands tilde to home directory."""
        # Create a directory that would be found via tilde expansion
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        agent_dir = fake_home / ".claude" / "agents"
        agent_dir.mkdir(parents=True)

        monkeypatch.setenv("HOME", str(fake_home))

        scanner = AgentScanner(["~/.claude/agents"])
        sources = scanner.discover_sources()

        assert len(sources) == 1

    def test_logs_missing_directories(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logs debug message for missing directories."""
        missing_path = "/nonexistent/path/agents"

        with caplog.at_level(logging.DEBUG):
            scanner = AgentScanner([missing_path])
            scanner.discover_sources()

        assert "not found (skipping)" in caplog.text


class TestAgentScannerScanDirectory:
    """Tests for scan_directory method."""

    def test_find_md_files(self, tmp_path: Path) -> None:
        """Finds .md files in directory."""
        (tmp_path / "agent1.md").write_text("# Agent 1")
        (tmp_path / "agent2.md").write_text("# Agent 2")
        (tmp_path / "readme.txt").write_text("Not an agent")

        scanner = AgentScanner()
        files = list(scanner.scan_directory(tmp_path))

        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"agent1.md", "agent2.md"}

    def test_find_markdown_extension(self, tmp_path: Path) -> None:
        """Finds .markdown files too."""
        (tmp_path / "agent.markdown").write_text("# Agent")

        scanner = AgentScanner()
        files = list(scanner.scan_directory(tmp_path))

        assert len(files) == 1
        assert files[0].name == "agent.markdown"

    def test_case_insensitive_extension(self, tmp_path: Path) -> None:
        """Handles case variations in extensions."""
        (tmp_path / "agent.MD").write_text("# Agent")
        (tmp_path / "agent2.Md").write_text("# Agent 2")

        scanner = AgentScanner()
        files = list(scanner.scan_directory(tmp_path))

        assert len(files) == 2

    def test_sorted_output(self, tmp_path: Path) -> None:
        """Returns files sorted alphabetically."""
        (tmp_path / "charlie.md").write_text("# C")
        (tmp_path / "alpha.md").write_text("# A")
        (tmp_path / "bravo.md").write_text("# B")

        scanner = AgentScanner()
        files = list(scanner.scan_directory(tmp_path))

        names = [f.name for f in files]
        assert names == ["alpha.md", "bravo.md", "charlie.md"]

    def test_skip_subdirectories(self, tmp_path: Path) -> None:
        """Does not recurse into subdirectories."""
        (tmp_path / "agent.md").write_text("# Agent")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.md").write_text("# Nested")

        scanner = AgentScanner()
        files = list(scanner.scan_directory(tmp_path))

        assert len(files) == 1
        assert files[0].name == "agent.md"

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Handles empty directory gracefully."""
        scanner = AgentScanner()
        files = list(scanner.scan_directory(tmp_path))

        assert files == []

    def test_nonexistent_directory(self, caplog: pytest.LogCaptureFixture) -> None:
        """Warns and yields nothing for nonexistent directory."""
        scanner = AgentScanner()

        with caplog.at_level(logging.WARNING):
            files = list(scanner.scan_directory(Path("/nonexistent")))

        assert files == []
        assert "does not exist" in caplog.text


class TestAgentScannerScanAllSources:
    """Tests for scan_all_sources method."""

    def test_scan_multiple_sources(self, tmp_path: Path) -> None:
        """Scans all source directories."""
        dir1 = tmp_path / "source1"
        dir1.mkdir()
        (dir1 / "agent1.md").write_text("# Agent 1")

        dir2 = tmp_path / "source2"
        dir2.mkdir()
        (dir2 / "agent2.md").write_text("# Agent 2")

        scanner = AgentScanner([str(dir1), str(dir2)])
        files = list(scanner.scan_all_sources())

        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"agent1.md", "agent2.md"}

    def test_no_sources_logs_info(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Logs info when no sources found."""
        scanner = AgentScanner([str(tmp_path / "nonexistent")])

        with caplog.at_level(logging.INFO):
            files = list(scanner.scan_all_sources())

        assert files == []
        assert "No agent source directories found" in caplog.text


class TestAgentScannerStats:
    """Tests for get_source_stats method."""

    def test_stats_per_source(self, tmp_path: Path) -> None:
        """Returns count per source directory."""
        dir1 = tmp_path / "source1"
        dir1.mkdir()
        (dir1 / "a.md").write_text("# A")
        (dir1 / "b.md").write_text("# B")

        dir2 = tmp_path / "source2"
        dir2.mkdir()
        (dir2 / "c.md").write_text("# C")

        scanner = AgentScanner([str(dir1), str(dir2)])
        stats = scanner.get_source_stats()

        assert stats[str(dir1)] == 2
        assert stats[str(dir2)] == 1

    def test_empty_stats(self, tmp_path: Path) -> None:
        """Returns empty stats when no sources exist."""
        scanner = AgentScanner([str(tmp_path / "nonexistent")])
        stats = scanner.get_source_stats()

        assert stats == {}


class TestDefaultDiscoveryPaths:
    """Tests for default path configuration."""

    def test_default_paths_list(self) -> None:
        """Default paths include all expected directories."""
        assert len(DEFAULT_DISCOVERY_PATHS) == 4
        assert "~/.claude/agents" in DEFAULT_DISCOVERY_PATHS
        assert "~/.config/ampcode/agents" in DEFAULT_DISCOVERY_PATHS
        assert "~/.config/droid/agent" in DEFAULT_DISCOVERY_PATHS
        assert "~/.config/opencode/agent" in DEFAULT_DISCOVERY_PATHS

    def test_supported_extensions(self) -> None:
        """Supported extensions include .md and .markdown."""
        assert ".md" in AGENT_FILE_EXTENSIONS
        assert ".markdown" in AGENT_FILE_EXTENSIONS
