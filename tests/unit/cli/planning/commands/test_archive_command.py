"""Unit tests for ArchiveCommand.

Tests basic import structure and Aurora path conventions.
"""

import pytest
import tempfile
from pathlib import Path

from aurora_cli.planning.commands import ArchiveCommand
from aurora_cli.planning.commands.archive import OperationCounts, SpecUpdate


class TestArchiveCommandImport:
    """Tests for ArchiveCommand module structure."""

    def test_archive_command_importable(self):
        """Verify ArchiveCommand can be imported."""
        assert ArchiveCommand is not None

    def test_archive_command_has_execute_method(self):
        """Verify ArchiveCommand has execute method."""
        command = ArchiveCommand()
        assert hasattr(command, 'execute')
        assert callable(command.execute)

    def test_spec_update_dataclass_exists(self):
        """Verify SpecUpdate dataclass is available."""
        assert SpecUpdate is not None

    def test_operation_counts_dataclass_exists(self):
        """Verify OperationCounts dataclass is available."""
        assert OperationCounts is not None
        counts = OperationCounts()
        assert counts.added == 0
        assert counts.modified == 0
        assert counts.removed == 0
        assert counts.renamed == 0


class TestArchiveCommandAuroraPaths:
    """Tests verifying Aurora path conventions are used."""

    def test_aurora_paths_used_in_execute(self):
        """Verify execute method uses Aurora directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            # ArchiveCommand should look for .aurora/plans/active
            command = ArchiveCommand()

            # Should raise error about Aurora plans directory not found
            with pytest.raises(RuntimeError) as exc_info:
                command.execute(plan_name="test-plan", target_path=str(target))

            # Error message should mention Aurora, not OpenSpec
            assert "Aurora" in str(exc_info.value)
            assert "aur plan init" in str(exc_info.value)
            assert "OpenSpec" not in str(exc_info.value)

    def test_build_spec_skeleton_uses_aurora_terminology(self):
        """Verify spec skeleton uses Aurora terminology."""
        command = ArchiveCommand()
        skeleton = command._build_spec_skeleton("test-feature", "plan-001")

        # Should use "Capability Specification" not just "Specification"
        assert "Capability Specification" in skeleton
        # Should reference "plan" not "change"
        assert "plan plan-001" in skeleton
        assert "change" not in skeleton.lower() or "changes" in skeleton.lower()  # Allow "Changes" in "What Changes"
