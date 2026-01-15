"""Tests for file change aggregation and conflict resolution."""

import tempfile
from pathlib import Path

import pytest

from aurora_cli.file_change_aggregator import (
    AggregationResult,
    ConflictType,
    FileChange,
    FileChangeAggregator,
    FileConflict,
    FileSnapshot,
    MergeStrategy,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for file change testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create some initial files
        (workspace / "test.py").write_text("def hello():\n    return 'hello'\n")
        (workspace / "config.json").write_text('{"key": "value"}\n')
        (workspace / "README.md").write_text("# Test Project\n")

        yield workspace


class TestFileSnapshot:
    """Tests for FileSnapshot class."""

    def test_capture_existing_file(self, temp_workspace):
        """Test capturing an existing file."""
        path = temp_workspace / "test.py"
        snapshot = FileSnapshot.capture(path)

        assert snapshot.exists
        assert snapshot.content == "def hello():\n    return 'hello'\n"
        assert snapshot.hash != ""
        assert snapshot.path == path

    def test_capture_nonexistent_file(self, temp_workspace):
        """Test capturing a non-existent file."""
        path = temp_workspace / "nonexistent.py"
        snapshot = FileSnapshot.capture(path)

        assert not snapshot.exists
        assert snapshot.content == ""
        assert snapshot.hash == ""

    def test_hash_changes_with_content(self, temp_workspace):
        """Test that hash changes when file content changes."""
        path = temp_workspace / "test.py"
        snapshot1 = FileSnapshot.capture(path)

        path.write_text("def goodbye():\n    return 'goodbye'\n")
        snapshot2 = FileSnapshot.capture(path)

        assert snapshot1.hash != snapshot2.hash


class TestFileChange:
    """Tests for FileChange class."""

    def test_is_creation(self, temp_workspace):
        """Test detecting file creation."""
        path = temp_workspace / "new_file.py"

        before = FileSnapshot(path=path, content="", hash="", exists=False)
        after = FileSnapshot(path=path, content="content", hash="abc", exists=True)

        change = FileChange(tool="claude", path=path, before=before, after=after)

        assert change.is_creation
        assert not change.is_deletion
        assert not change.is_modification

    def test_is_deletion(self, temp_workspace):
        """Test detecting file deletion."""
        path = temp_workspace / "deleted_file.py"

        before = FileSnapshot(path=path, content="content", hash="abc", exists=True)
        after = FileSnapshot(path=path, content="", hash="", exists=False)

        change = FileChange(tool="claude", path=path, before=before, after=after)

        assert change.is_deletion
        assert not change.is_creation
        assert not change.is_modification

    def test_is_modification(self, temp_workspace):
        """Test detecting file modification."""
        path = temp_workspace / "modified_file.py"

        before = FileSnapshot(path=path, content="old", hash="abc", exists=True)
        after = FileSnapshot(path=path, content="new", hash="def", exists=True)

        change = FileChange(tool="claude", path=path, before=before, after=after)

        assert change.is_modification
        assert not change.is_creation
        assert not change.is_deletion

    def test_has_changes(self, temp_workspace):
        """Test detecting if change has actual changes."""
        path = temp_workspace / "file.py"

        # No change
        before = FileSnapshot(path=path, content="same", hash="abc", exists=True)
        after = FileSnapshot(path=path, content="same", hash="abc", exists=True)
        change = FileChange(tool="claude", path=path, before=before, after=after)
        assert not change.has_changes

        # Has change
        after = FileSnapshot(path=path, content="different", hash="def", exists=True)
        change = FileChange(tool="claude", path=path, before=before, after=after)
        assert change.has_changes

    def test_get_diff(self, temp_workspace):
        """Test generating diff for a change."""
        path = temp_workspace / "test.py"

        before = FileSnapshot(path=path, content="line1\nline2\n", hash="abc", exists=True)
        after = FileSnapshot(path=path, content="line1\nline2\nline3\n", hash="def", exists=True)

        change = FileChange(tool="claude", path=path, before=before, after=after)
        diff = change.get_diff()

        assert "+line3" in diff
        assert "claude" in diff


class TestFileChangeAggregator:
    """Tests for FileChangeAggregator class."""

    def test_capture_before_and_after(self, temp_workspace):
        """Test capturing file state before and after tool execution."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py", "**/*.json"],
        )

        # Capture before state
        aggregator.capture_before()

        # Simulate tool making changes
        (temp_workspace / "test.py").write_text("def hello():\n    return 'world'\n")

        # Capture after state for tool1
        changes = aggregator.capture_after("tool1")

        assert len(changes) == 1
        assert changes[0].tool == "tool1"
        assert changes[0].path == temp_workspace / "test.py"
        assert changes[0].is_modification

    def test_detect_no_conflicts_single_tool(self, temp_workspace):
        """Test no conflicts with single tool."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("modified content")
        aggregator.capture_after("tool1")

        conflicts = aggregator.detect_conflicts()
        assert len(conflicts) == 0

    def test_detect_conflicts_overlapping_changes(self, temp_workspace):
        """Test detecting conflicts when tools modify same file."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        # First tool makes changes
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool1 modification line 1\nline 2\n")
        aggregator.capture_after("tool1")

        # Reset and second tool makes different changes
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool2 modification line 1\nline 2 different\n")
        aggregator.capture_after("tool2")

        conflicts = aggregator.detect_conflicts()

        assert len(conflicts) == 1
        assert conflicts[0].path == temp_workspace / "test.py"
        assert conflicts[0].conflict_type != ConflictType.NONE

    def test_detect_no_conflict_identical_changes(self, temp_workspace):
        """Test no conflict when tools make identical changes."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        # First tool
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("identical content")
        aggregator.capture_after("tool1")

        # Reset to original
        (temp_workspace / "test.py").write_text("def hello():\n    return 'hello'\n")

        # Second tool makes same change
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("identical content")
        aggregator.capture_after("tool2")

        conflicts = aggregator.detect_conflicts()

        # Should detect it as a potential conflict but mark as NONE severity
        if conflicts:
            assert conflicts[0].conflict_type == ConflictType.NONE

    def test_detect_delete_modify_conflict(self, temp_workspace):
        """Test detecting delete/modify conflict."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        # First tool deletes
        aggregator.capture_before()
        (temp_workspace / "test.py").unlink()
        aggregator.capture_after("tool1")

        # Create file again for second tool
        (temp_workspace / "test.py").write_text("new content")

        # Second tool modifies
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("modified content")
        aggregator.capture_after("tool2")

        conflicts = aggregator.detect_conflicts()

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.DELETE_MODIFY

    def test_resolve_prefer_first(self, temp_workspace):
        """Test resolving conflicts with PREFER_FIRST strategy."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        # Setup conflicting changes
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool1 content")
        aggregator.capture_after("tool1")

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool2 content")
        aggregator.capture_after("tool2")

        result = aggregator.resolve(strategy=MergeStrategy.PREFER_FIRST)

        assert result.success
        assert temp_workspace / "test.py" in result.merged_changes
        assert result.merged_changes[temp_workspace / "test.py"] == "tool1 content"

    def test_resolve_prefer_last(self, temp_workspace):
        """Test resolving conflicts with PREFER_LAST strategy."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        # Setup conflicting changes
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool1 content")
        aggregator.capture_after("tool1")

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool2 content")
        aggregator.capture_after("tool2")

        result = aggregator.resolve(strategy=MergeStrategy.PREFER_LAST)

        assert result.success
        assert temp_workspace / "test.py" in result.merged_changes
        assert result.merged_changes[temp_workspace / "test.py"] == "tool2 content"

    def test_resolve_abort_on_conflict(self, temp_workspace):
        """Test resolving with ABORT strategy fails on conflict."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        # Setup conflicting changes
        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool1 content")
        aggregator.capture_after("tool1")

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("tool2 content")
        aggregator.capture_after("tool2")

        result = aggregator.resolve(strategy=MergeStrategy.ABORT)

        # ABORT should leave conflicts unresolved
        assert not result.success or result.has_conflicts

    def test_apply_merged_changes(self, temp_workspace):
        """Test applying merged changes to filesystem."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("new content")
        aggregator.capture_after("tool1")

        result = aggregator.resolve(strategy=MergeStrategy.PREFER_FIRST)
        applied = aggregator.apply_merged_changes(result)

        assert all(applied.values())
        assert (temp_workspace / "test.py").read_text() == "new content"

    def test_apply_merged_changes_dry_run(self, temp_workspace):
        """Test dry run doesn't actually modify files."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        original_content = (temp_workspace / "test.py").read_text()

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("new content")
        aggregator.capture_after("tool1")

        # Restore original before dry run
        (temp_workspace / "test.py").write_text(original_content)

        result = aggregator.resolve(strategy=MergeStrategy.PREFER_FIRST)
        applied = aggregator.apply_merged_changes(result, dry_run=True)

        # File should still have original content
        assert (temp_workspace / "test.py").read_text() == original_content

    def test_get_summary(self, temp_workspace):
        """Test getting human-readable summary."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("modified")
        aggregator.capture_after("tool1")

        summary = aggregator.get_summary()

        assert "tool1" in summary
        assert "test.py" in summary

    def test_reset_clears_state(self, temp_workspace):
        """Test reset clears all tracked state."""
        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.py"],
        )

        aggregator.capture_before()
        (temp_workspace / "test.py").write_text("modified")
        aggregator.capture_after("tool1")

        aggregator.reset()

        # After reset, should have no changes
        conflicts = aggregator.detect_conflicts()
        assert len(conflicts) == 0

    def test_ignore_patterns(self, temp_workspace):
        """Test that ignore patterns are respected."""
        # Create a node_modules directory with files
        node_modules = temp_workspace / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("module.exports = {}")

        aggregator = FileChangeAggregator(
            working_dir=temp_workspace,
            track_patterns=["**/*.js"],
            ignore_patterns=["**/node_modules/**"],
        )

        aggregator.capture_before()
        (node_modules / "package.js").write_text("modified")
        changes = aggregator.capture_after("tool1")

        # Should not track changes in ignored directories
        assert len(changes) == 0


class TestFileConflict:
    """Tests for FileConflict class."""

    def test_get_conflict_markers(self, temp_workspace):
        """Test generating git-style conflict markers."""
        path = temp_workspace / "test.py"

        change1 = FileChange(
            tool="tool1",
            path=path,
            before=FileSnapshot(path=path, content="original", hash="a", exists=True),
            after=FileSnapshot(path=path, content="tool1 change", hash="b", exists=True),
        )
        change2 = FileChange(
            tool="tool2",
            path=path,
            before=FileSnapshot(path=path, content="original", hash="a", exists=True),
            after=FileSnapshot(path=path, content="tool2 change", hash="c", exists=True),
        )

        conflict = FileConflict(
            path=path,
            conflict_type=ConflictType.OVERLAPPING_LINES,
            changes=[change1, change2],
            description="Test conflict",
        )

        markers = conflict.get_conflict_markers()

        assert "<<<<<<< tool1" in markers
        assert "tool1 change" in markers
        assert "=======" in markers
        assert "tool2 change" in markers
        assert ">>>>>>> tool2" in markers


class TestAggregationResult:
    """Tests for AggregationResult class."""

    def test_has_conflicts(self, temp_workspace):
        """Test has_conflicts property."""
        path = temp_workspace / "test.py"

        # Result with no conflicts
        result = AggregationResult(
            success=True,
            strategy_used=MergeStrategy.PREFER_FIRST,
            files_changed=[path],
            conflicts=[],
            merged_changes={path: "content"},
        )
        assert not result.has_conflicts

        # Result with conflicts
        conflict = FileConflict(
            path=path,
            conflict_type=ConflictType.OVERLAPPING_LINES,
            changes=[],
            description="Test",
        )
        result.conflicts.append(conflict)
        assert result.has_conflicts

    def test_unresolved_conflicts(self, temp_workspace):
        """Test unresolved_conflicts property."""
        path = temp_workspace / "test.py"

        resolved_conflict = FileConflict(
            path=path,
            conflict_type=ConflictType.OVERLAPPING_LINES,
            changes=[],
            description="Resolved",
            resolved_content="resolved content",
        )
        unresolved_conflict = FileConflict(
            path=temp_workspace / "other.py",
            conflict_type=ConflictType.DIVERGENT_LOGIC,
            changes=[],
            description="Unresolved",
        )

        result = AggregationResult(
            success=False,
            strategy_used=MergeStrategy.ABORT,
            files_changed=[path],
            conflicts=[resolved_conflict, unresolved_conflict],
            merged_changes={},
        )

        assert len(result.unresolved_conflicts) == 1
        assert result.unresolved_conflicts[0] == unresolved_conflict
