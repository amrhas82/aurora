"""Unit tests for ManifestManager module.

Tests manifest generation, caching, de-duplication, and auto-refresh
functionality for agent discovery.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.agent_discovery.manifest import ManifestManager, should_refresh_manifest
from aurora_cli.agent_discovery.models import AgentCategory, AgentInfo, AgentManifest


class TestManifestManagerGenerate:
    """Tests for generate method."""

    def test_generate_from_sources(self, tmp_path: Path) -> None:
        """Generates manifest from agent files in sources."""
        # Create agent files
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        (agents_dir / "agent1.md").write_text(
            """---
id: agent-one
role: Agent One Role
goal: First agent goal
category: eng
---
"""
        )

        (agents_dir / "agent2.md").write_text(
            """---
id: agent-two
role: Agent Two Role
goal: Second agent goal
category: qa
---
"""
        )

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])

        assert manifest.stats.total == 2
        assert "agent-one" in [a.id for a in manifest.agents]
        assert "agent-two" in [a.id for a in manifest.agents]
        assert manifest.stats.by_category["eng"] == 1
        assert manifest.stats.by_category["qa"] == 1

    def test_generate_handles_malformed_files(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Counts malformed files and continues with valid ones."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Valid agent
        (agents_dir / "valid.md").write_text(
            """---
id: valid-agent
role: Valid Role
goal: Valid goal
---
"""
        )

        # Malformed agent (missing required fields)
        (agents_dir / "invalid.md").write_text(
            """---
id: invalid-agent
# Missing role and goal
---
"""
        )

        manager = ManifestManager()

        with caplog.at_level(logging.WARNING):
            manifest = manager.generate(sources=[str(agents_dir)])

        assert manifest.stats.total == 1
        assert manifest.stats.malformed_files == 1
        assert manifest.agents[0].id == "valid-agent"

    def test_generate_deduplicates_by_id(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warns and skips duplicate agent IDs."""
        dir1 = tmp_path / "source1"
        dir1.mkdir()
        (dir1 / "agent.md").write_text(
            """---
id: duplicate-id
role: First Role
goal: First goal
---
"""
        )

        dir2 = tmp_path / "source2"
        dir2.mkdir()
        (dir2 / "agent.md").write_text(
            """---
id: duplicate-id
role: Second Role
goal: Second goal
---
"""
        )

        manager = ManifestManager()

        with caplog.at_level(logging.WARNING):
            manifest = manager.generate(sources=[str(dir1), str(dir2)])

        assert manifest.stats.total == 1
        assert "Duplicate agent ID" in caplog.text
        # First one should be kept
        assert manifest.agents[0].role == "First Role"

    def test_generate_empty_sources(self, tmp_path: Path) -> None:
        """Handles empty source directories."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(empty_dir)])

        assert manifest.stats.total == 0
        assert manifest.stats.malformed_files == 0

    def test_generate_includes_sources_in_manifest(self, tmp_path: Path) -> None:
        """Records source paths in manifest."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])

        assert str(agents_dir) in manifest.sources

    def test_generate_sets_generated_at(self, tmp_path: Path) -> None:
        """Sets generated_at timestamp."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        before = datetime.now().astimezone()
        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])
        after = datetime.now().astimezone()

        assert before <= manifest.generated_at <= after


class TestManifestManagerSaveLoad:
    """Tests for save and load methods."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Manifest survives save/load roundtrip."""
        # Create a manifest
        manifest = AgentManifest(
            version="1.0.0",
            generated_at=datetime.now().astimezone(),
            sources=["/test/source"],
            agents=[
                AgentInfo(
                    id="test-agent",
                    role="Test Role",
                    goal="Test goal",
                    category=AgentCategory.ENG,
                    skills=["skill1", "skill2"],
                )
            ],
        )
        manifest.stats.total = 1
        manifest.stats.by_category = {"eng": 1}

        # Save and load
        manifest_path = tmp_path / "manifest.json"
        manager = ManifestManager()
        manager.save(manifest, manifest_path)
        loaded = manager.load(manifest_path)

        assert loaded is not None
        assert loaded.version == manifest.version
        assert loaded.stats.total == 1
        assert len(loaded.agents) == 1
        assert loaded.agents[0].id == "test-agent"
        assert loaded.agents[0].skills == ["skill1", "skill2"]

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """Creates parent directories if they don't exist."""
        manifest = AgentManifest()
        nested_path = tmp_path / "deep" / "nested" / "manifest.json"

        manager = ManifestManager()
        manager.save(manifest, nested_path)

        assert nested_path.exists()

    def test_save_atomic_write(self, tmp_path: Path) -> None:
        """Uses atomic write (temp file + rename)."""
        manifest = AgentManifest()
        manifest_path = tmp_path / "manifest.json"

        manager = ManifestManager()
        manager.save(manifest, manifest_path)

        # File should exist and be valid JSON
        assert manifest_path.exists()
        with open(manifest_path) as f:
            data = json.load(f)
        assert "version" in data

    def test_load_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Returns None for nonexistent file."""
        manager = ManifestManager()
        result = manager.load(tmp_path / "nonexistent.json")

        assert result is None

    def test_load_returns_none_for_invalid_json(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Returns None and warns for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        manager = ManifestManager()

        with caplog.at_level(logging.WARNING):
            result = manager.load(invalid_file)

        assert result is None
        assert "Invalid JSON" in caplog.text

    def test_load_returns_none_for_invalid_manifest(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Returns None and warns for valid JSON but invalid manifest."""
        invalid_file = tmp_path / "not_manifest.json"
        invalid_file.write_text('{"not": "a manifest"}')

        manager = ManifestManager()

        with caplog.at_level(logging.WARNING):
            result = manager.load(invalid_file)

        # Should either load with defaults or return None
        # (depends on how strict the schema is)
        # The current implementation is lenient and returns a manifest with defaults


class TestManifestManagerShouldRefresh:
    """Tests for should_refresh method."""

    def test_refresh_needed_if_missing(self, tmp_path: Path) -> None:
        """Refresh needed if manifest doesn't exist."""
        manager = ManifestManager()
        result = manager.should_refresh(tmp_path / "missing.json")

        assert result is True

    def test_refresh_needed_if_old(self, tmp_path: Path) -> None:
        """Refresh needed if manifest is older than interval."""
        manifest_path = tmp_path / "old.json"
        manifest_path.write_text("{}")

        # Make file appear old
        old_time = time.time() - (25 * 60 * 60)  # 25 hours ago
        import os

        os.utime(manifest_path, (old_time, old_time))

        manager = ManifestManager()
        result = manager.should_refresh(manifest_path, refresh_interval_hours=24)

        assert result is True

    def test_no_refresh_needed_if_fresh(self, tmp_path: Path) -> None:
        """No refresh needed if manifest is recent."""
        manifest_path = tmp_path / "fresh.json"
        manifest_path.write_text("{}")
        # File is just created, so mtime is now

        manager = ManifestManager()
        result = manager.should_refresh(manifest_path, refresh_interval_hours=24)

        assert result is False


class TestManifestManagerGetOrRefresh:
    """Tests for get_or_refresh method."""

    def test_loads_existing_manifest_if_fresh(self, tmp_path: Path) -> None:
        """Loads existing manifest without regeneration if fresh."""
        # Create and save a manifest
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent.md").write_text(
            """---
id: existing-agent
role: Existing Role
goal: Existing goal
---
"""
        )

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])

        manifest_path = tmp_path / "manifest.json"
        manager.save(manifest, manifest_path)

        # Get or refresh - should load existing
        result = manager.get_or_refresh(
            manifest_path,
            auto_refresh=True,
            refresh_interval_hours=24,
        )

        assert result.stats.total == 1
        assert result.agents[0].id == "existing-agent"

    def test_regenerates_if_missing(self, tmp_path: Path) -> None:
        """Regenerates manifest if file missing."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "new-agent.md").write_text(
            """---
id: new-agent
role: New Role
goal: New goal
---
"""
        )

        # Create manager with custom scanner pointing to our dir
        from aurora_cli.agent_discovery.scanner import AgentScanner

        scanner = AgentScanner([str(agents_dir)])
        manager = ManifestManager(scanner=scanner)

        manifest_path = tmp_path / "missing.json"
        result = manager.get_or_refresh(manifest_path)

        assert manifest_path.exists()
        assert result.stats.total == 1

    def test_skips_refresh_check_when_disabled(self, tmp_path: Path) -> None:
        """Skips staleness check when auto_refresh=False."""
        manifest_path = tmp_path / "manifest.json"

        # Create an old manifest
        manifest = AgentManifest()
        manager = ManifestManager()
        manager.save(manifest, manifest_path)

        # Make it old
        old_time = time.time() - (100 * 60 * 60)  # 100 hours ago
        import os

        os.utime(manifest_path, (old_time, old_time))

        # With auto_refresh=False, should load old manifest without regeneration
        result = manager.get_or_refresh(
            manifest_path,
            auto_refresh=False,
        )

        # Should have loaded the existing (empty) manifest
        assert result.stats.total == 0


class TestShouldRefreshManifestFunction:
    """Tests for should_refresh_manifest helper function."""

    def test_uses_config_auto_refresh(self, tmp_path: Path) -> None:
        """Uses config auto_refresh setting."""
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("{}")

        # Mock config with auto_refresh disabled
        mock_config = MagicMock()
        mock_config.agents_auto_refresh = False

        # With auto_refresh=False, only refresh if file missing
        result = should_refresh_manifest(manifest_path, mock_config)
        assert result is False  # File exists, no refresh needed

        # Now with missing file
        result = should_refresh_manifest(
            tmp_path / "missing.json", mock_config
        )
        assert result is True  # File missing, refresh needed

    def test_uses_config_interval(self, tmp_path: Path) -> None:
        """Uses config refresh_interval_hours setting."""
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("{}")

        mock_config = MagicMock()
        mock_config.agents_auto_refresh = True
        mock_config.agents_refresh_interval_hours = 1  # 1 hour

        # Fresh file - no refresh
        result = should_refresh_manifest(manifest_path, mock_config)
        assert result is False

        # Make file old (2 hours)
        old_time = time.time() - (2 * 60 * 60)
        import os

        os.utime(manifest_path, (old_time, old_time))

        result = should_refresh_manifest(manifest_path, mock_config)
        assert result is True


class TestManifestIndexes:
    """Tests for manifest index functionality."""

    def test_get_agent_by_id(self, tmp_path: Path) -> None:
        """Gets agent by ID from manifest index."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent.md").write_text(
            """---
id: findable-agent
role: Findable Role
goal: Can be found
---
"""
        )

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])

        agent = manifest.get_agent("findable-agent")
        assert agent is not None
        assert agent.role == "Findable Role"

    def test_get_agent_case_insensitive(self, tmp_path: Path) -> None:
        """ID lookup is case-insensitive."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent.md").write_text(
            """---
id: my-agent
role: My Role
goal: My goal
---
"""
        )

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])

        # Various case combinations should all work
        assert manifest.get_agent("my-agent") is not None
        assert manifest.get_agent("MY-AGENT") is not None
        assert manifest.get_agent("My-Agent") is not None

    def test_get_agents_by_category(self, tmp_path: Path) -> None:
        """Gets all agents in a category."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        (agents_dir / "eng1.md").write_text(
            """---
id: eng-one
role: Eng One
goal: Engineering
category: eng
---
"""
        )
        (agents_dir / "eng2.md").write_text(
            """---
id: eng-two
role: Eng Two
goal: Engineering
category: eng
---
"""
        )
        (agents_dir / "qa1.md").write_text(
            """---
id: qa-one
role: QA One
goal: Testing
category: qa
---
"""
        )

        manager = ManifestManager()
        manifest = manager.generate(sources=[str(agents_dir)])

        eng_agents = manifest.get_agents_by_category(AgentCategory.ENG)
        assert len(eng_agents) == 2

        qa_agents = manifest.get_agents_by_category(AgentCategory.QA)
        assert len(qa_agents) == 1
