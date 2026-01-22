"""File change aggregation and conflict resolution for multi-tool execution.

When multiple tools (Claude, OpenCode) run concurrently on the same codebase,
they may produce overlapping file edits. This module detects, reports, and
resolves these conflicts.

Example:
    aggregator = FileChangeAggregator(working_dir=Path.cwd())

    # Track changes from each tool
    aggregator.capture_before()  # Snapshot before execution
    # ... tool1 executes ...
    aggregator.capture_after("claude")
    aggregator.capture_before()
    # ... tool2 executes ...
    aggregator.capture_after("opencode")

    # Analyze and resolve conflicts
    result = aggregator.resolve(strategy=MergeStrategy.PREFER_FIRST)

"""

from __future__ import annotations

import difflib
import hashlib
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Strategy for resolving file conflicts between tools."""

    PREFER_FIRST = "prefer_first"  # Keep first tool's changes
    PREFER_LAST = "prefer_last"  # Keep last tool's changes
    UNION = "union"  # Keep all non-conflicting changes, mark conflicts
    INTERACTIVE = "interactive"  # Prompt user for each conflict
    SMART_MERGE = "smart_merge"  # Attempt semantic merge based on change type
    ABORT = "abort"  # Abort on any conflict


class ConflictType(Enum):
    """Type of conflict between file changes."""

    NONE = "none"  # No conflict
    OVERLAPPING_LINES = "overlapping_lines"  # Both modified same lines
    DIVERGENT_LOGIC = "divergent_logic"  # Different approaches to same problem
    STRUCTURAL = "structural"  # Incompatible structural changes
    DELETE_MODIFY = "delete_modify"  # One deleted, other modified


@dataclass
class FileSnapshot:
    """Snapshot of a file's state."""

    path: Path
    content: str
    hash: str
    exists: bool
    mtime: float = 0.0

    @classmethod
    def capture(cls, path: Path) -> FileSnapshot:
        """Capture current state of a file."""
        if not path.exists():
            return cls(
                path=path,
                content="",
                hash="",
                exists=False,
            )

        content = path.read_text(encoding="utf-8", errors="replace")
        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        return cls(
            path=path,
            content=content,
            hash=file_hash,
            exists=True,
            mtime=path.stat().st_mtime,
        )


@dataclass
class FileChange:
    """A change made to a file by a tool."""

    tool: str
    path: Path
    before: FileSnapshot
    after: FileSnapshot
    diff_lines: list[str] = field(default_factory=list)
    change_type: str = "modified"  # created, modified, deleted

    @property
    def is_creation(self) -> bool:
        return not self.before.exists and self.after.exists

    @property
    def is_deletion(self) -> bool:
        return self.before.exists and not self.after.exists

    @property
    def is_modification(self) -> bool:
        return self.before.exists and self.after.exists and self.before.hash != self.after.hash

    @property
    def has_changes(self) -> bool:
        return self.before.hash != self.after.hash

    def get_diff(self) -> str:
        """Get unified diff of the change."""
        if not self.diff_lines:
            before_lines = self.before.content.splitlines(keepends=True)
            after_lines = self.after.content.splitlines(keepends=True)
            self.diff_lines = list(
                difflib.unified_diff(
                    before_lines,
                    after_lines,
                    fromfile=f"{self.path} (before {self.tool})",
                    tofile=f"{self.path} (after {self.tool})",
                    n=3,
                ),
            )
        return "".join(self.diff_lines)


@dataclass
class FileConflict:
    """A conflict between changes from different tools."""

    path: Path
    conflict_type: ConflictType
    changes: list[FileChange]
    description: str
    resolution: str | None = None
    resolved_content: str | None = None

    def get_conflict_markers(self) -> str:
        """Generate git-style conflict markers."""
        if len(self.changes) < 2:
            return ""

        lines = []
        lines.append(f"<<<<<<< {self.changes[0].tool}")
        lines.append(self.changes[0].after.content)
        lines.append("=======")
        lines.append(self.changes[1].after.content)
        lines.append(f">>>>>>> {self.changes[1].tool}")
        return "\n".join(lines)


@dataclass
class AggregationResult:
    """Result of file change aggregation."""

    success: bool
    strategy_used: MergeStrategy
    files_changed: list[Path]
    conflicts: list[FileConflict]
    merged_changes: dict[Path, str]  # path -> resolved content
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def unresolved_conflicts(self) -> list[FileConflict]:
        return [c for c in self.conflicts if c.resolved_content is None]


class FileChangeAggregator:
    """Aggregates and resolves file changes from multiple tools.

    Tracks file states before and after each tool execution, detects conflicts,
    and provides resolution strategies.
    """

    def __init__(
        self,
        working_dir: Path | None = None,
        track_patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        """Initialize aggregator.

        Args:
            working_dir: Working directory to track (default: cwd)
            track_patterns: Glob patterns to track (default: common code files)
            ignore_patterns: Glob patterns to ignore (default: node_modules, .git, etc.)

        """
        self.working_dir = working_dir or Path.cwd()
        self.track_patterns = track_patterns or [
            "**/*.py",
            "**/*.js",
            "**/*.ts",
            "**/*.tsx",
            "**/*.json",
            "**/*.yaml",
            "**/*.yml",
            "**/*.md",
            "**/*.html",
            "**/*.css",
            "**/*.scss",
        ]
        self.ignore_patterns = ignore_patterns or [
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/venv/**",
            "**/.env/**",
            "**/dist/**",
            "**/build/**",
            "**/*.pyc",
        ]

        self._snapshots: dict[str, dict[Path, FileSnapshot]] = {}
        self._changes: dict[str, list[FileChange]] = {}
        self._current_snapshot: dict[Path, FileSnapshot] = {}

    def _should_track(self, path: Path) -> bool:
        """Check if a path should be tracked."""
        # Check ignore patterns first
        for pattern in self.ignore_patterns:
            if path.match(pattern):
                return False

        # Check track patterns
        for pattern in self.track_patterns:
            if path.match(pattern):
                return True

        return False

    def _get_tracked_files(self) -> list[Path]:
        """Get list of all tracked files in working directory."""
        files = []
        for pattern in self.track_patterns:
            for path in self.working_dir.glob(pattern):
                if path.is_file() and self._should_track(path):
                    files.append(path)
        return sorted(set(files))

    def capture_before(self) -> None:
        """Capture file states before tool execution."""
        self._current_snapshot = {}
        for path in self._get_tracked_files():
            self._current_snapshot[path] = FileSnapshot.capture(path)

    def capture_after(self, tool: str) -> list[FileChange]:
        """Capture file states after tool execution and compute changes.

        Args:
            tool: Name of the tool that made changes

        Returns:
            List of FileChange objects for files that changed

        """
        if tool not in self._changes:
            self._changes[tool] = []
            self._snapshots[tool] = {}

        changes = []
        current_files = set(self._get_tracked_files())
        before_files = set(self._current_snapshot.keys())

        # Check modified and deleted files
        for path in before_files:
            before = self._current_snapshot[path]
            after = FileSnapshot.capture(path)

            if before.hash != after.hash:
                change = FileChange(
                    tool=tool,
                    path=path,
                    before=before,
                    after=after,
                    change_type="deleted" if not after.exists else "modified",
                )
                changes.append(change)

            self._snapshots[tool][path] = after

        # Check for new files
        new_files = current_files - before_files
        for path in new_files:
            after = FileSnapshot.capture(path)
            before = FileSnapshot(
                path=path,
                content="",
                hash="",
                exists=False,
            )
            change = FileChange(
                tool=tool,
                path=path,
                before=before,
                after=after,
                change_type="created",
            )
            changes.append(change)
            self._snapshots[tool][path] = after

        self._changes[tool].extend(changes)
        return changes

    def capture_git_changes(self, tool: str) -> list[FileChange]:
        """Capture changes using git diff (more accurate for git repos).

        Args:
            tool: Name of the tool that made changes

        Returns:
            List of FileChange objects for files that changed

        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status"],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return self.capture_after(tool)

            changes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                status, *paths = parts
                path = self.working_dir / paths[0]

                if not self._should_track(path):
                    continue

                before = self._current_snapshot.get(
                    path,
                    FileSnapshot(
                        path=path,
                        content="",
                        hash="",
                        exists=False,
                    ),
                )
                after = FileSnapshot.capture(path)

                change_type = {
                    "M": "modified",
                    "A": "created",
                    "D": "deleted",
                    "R": "renamed",
                }.get(status[0], "modified")

                change = FileChange(
                    tool=tool,
                    path=path,
                    before=before,
                    after=after,
                    change_type=change_type,
                )
                changes.append(change)

            if tool not in self._changes:
                self._changes[tool] = []
            self._changes[tool].extend(changes)
            return changes

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self.capture_after(tool)

    def detect_conflicts(self) -> list[FileConflict]:
        """Detect conflicts between changes from different tools.

        Returns:
            List of FileConflict objects describing detected conflicts

        """
        conflicts = []

        # Group changes by file path
        changes_by_path: dict[Path, list[FileChange]] = {}
        for tool_changes in self._changes.values():
            for change in tool_changes:
                if change.path not in changes_by_path:
                    changes_by_path[change.path] = []
                changes_by_path[change.path].append(change)

        # Check each file with multiple changes
        for path, file_changes in changes_by_path.items():
            if len(file_changes) < 2:
                continue

            # Check for actual conflicts
            conflict = self._analyze_conflict(path, file_changes)
            if conflict.conflict_type != ConflictType.NONE:
                conflicts.append(conflict)

        return conflicts

    def _analyze_conflict(
        self,
        path: Path,
        changes: list[FileChange],
    ) -> FileConflict:
        """Analyze changes to a single file for conflicts."""
        # Check for delete/modify conflicts
        deletions = [c for c in changes if c.is_deletion]
        modifications = [c for c in changes if c.is_modification]

        if deletions and modifications:
            return FileConflict(
                path=path,
                conflict_type=ConflictType.DELETE_MODIFY,
                changes=changes,
                description=f"Conflict: {deletions[0].tool} deleted, {modifications[0].tool} modified",
            )

        # If only one tool made actual changes, no conflict
        actual_changes = [c for c in changes if c.has_changes]
        if len(actual_changes) <= 1:
            return FileConflict(
                path=path,
                conflict_type=ConflictType.NONE,
                changes=changes,
                description="No conflict",
            )

        # Check if changes are identical
        contents = [c.after.content for c in actual_changes]
        if len(set(contents)) == 1:
            return FileConflict(
                path=path,
                conflict_type=ConflictType.NONE,
                changes=changes,
                description="Identical changes from multiple tools",
            )

        # Analyze overlapping lines
        overlap = self._find_overlapping_changes(actual_changes)
        if overlap:
            return FileConflict(
                path=path,
                conflict_type=ConflictType.OVERLAPPING_LINES,
                changes=changes,
                description=f"Tools modified overlapping lines: {overlap}",
            )

        # Different non-overlapping changes - might be mergeable
        return FileConflict(
            path=path,
            conflict_type=ConflictType.DIVERGENT_LOGIC,
            changes=changes,
            description="Tools made different changes to the same file",
        )

    def _find_overlapping_changes(
        self,
        changes: list[FileChange],
    ) -> str | None:
        """Find overlapping line changes between tools."""
        if len(changes) < 2:
            return None

        # Get changed line ranges for each tool
        change_ranges: dict[str, set[int]] = {}
        for change in changes:
            before_lines = change.before.content.splitlines()
            after_lines = change.after.content.splitlines()

            matcher = difflib.SequenceMatcher(None, before_lines, after_lines)
            changed_lines: set[int] = set()

            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag != "equal":
                    changed_lines.update(range(i1, i2))

            change_ranges[change.tool] = changed_lines

        # Check for overlaps
        tools = list(change_ranges.keys())
        for i, tool1 in enumerate(tools):
            for tool2 in tools[i + 1 :]:
                overlap = change_ranges[tool1] & change_ranges[tool2]
                if overlap:
                    return f"{tool1} & {tool2} both modified lines {sorted(overlap)[:5]}"

        return None

    def resolve(
        self,
        strategy: MergeStrategy = MergeStrategy.PREFER_FIRST,
    ) -> AggregationResult:
        """Resolve conflicts and produce final merged state.

        Args:
            strategy: Strategy to use for conflict resolution

        Returns:
            AggregationResult with merged changes

        """
        conflicts = self.detect_conflicts()
        merged_changes: dict[Path, str] = {}
        files_changed: list[Path] = []

        # Collect all changed files
        all_changes: dict[Path, list[FileChange]] = {}
        for tool_changes in self._changes.values():
            for change in tool_changes:
                if change.path not in all_changes:
                    all_changes[change.path] = []
                all_changes[change.path].append(change)
                if change.path not in files_changed:
                    files_changed.append(change.path)

        # Resolve each file
        for path, changes in all_changes.items():
            # Find if there's a conflict for this path
            conflict = next((c for c in conflicts if c.path == path), None)

            if conflict and conflict.conflict_type != ConflictType.NONE:
                resolved = self._resolve_conflict(conflict, strategy)
                if resolved is not None:
                    merged_changes[path] = resolved
                    conflict.resolved_content = resolved
            else:
                # No conflict, use the change
                actual_changes = [c for c in changes if c.has_changes]
                if actual_changes:
                    merged_changes[path] = actual_changes[0].after.content

        # Check for unresolved conflicts
        unresolved = [
            c
            for c in conflicts
            if c.conflict_type != ConflictType.NONE and c.resolved_content is None
        ]

        return AggregationResult(
            success=len(unresolved) == 0,
            strategy_used=strategy,
            files_changed=files_changed,
            conflicts=conflicts,
            merged_changes=merged_changes,
            metadata={
                "total_conflicts": len(conflicts),
                "resolved_conflicts": len(conflicts) - len(unresolved),
                "tools_involved": list(self._changes.keys()),
            },
        )

    def _resolve_conflict(
        self,
        conflict: FileConflict,
        strategy: MergeStrategy,
    ) -> str | None:
        """Resolve a single conflict using the specified strategy."""
        if strategy == MergeStrategy.ABORT:
            return None

        actual_changes = [c for c in conflict.changes if c.has_changes]
        if not actual_changes:
            return None

        if strategy == MergeStrategy.PREFER_FIRST:
            return actual_changes[0].after.content

        if strategy == MergeStrategy.PREFER_LAST:
            return actual_changes[-1].after.content

        if strategy == MergeStrategy.UNION:
            return self._merge_union(conflict)

        if strategy == MergeStrategy.SMART_MERGE:
            return self._smart_merge(conflict)

        return None

    def _merge_union(self, conflict: FileConflict) -> str:
        """Merge changes, keeping all non-overlapping edits."""
        actual_changes = [c for c in conflict.changes if c.has_changes]
        if len(actual_changes) < 2:
            return actual_changes[0].after.content if actual_changes else ""

        # Start with the original content
        base_content = actual_changes[0].before.content
        base_lines = base_content.splitlines(keepends=True)

        # Apply non-overlapping changes from each tool
        # This is a simplified implementation - a full 3-way merge would be more robust
        result_lines = list(base_lines)

        for change in actual_changes:
            after_lines = change.after.content.splitlines(keepends=True)
            matcher = difflib.SequenceMatcher(None, base_lines, after_lines)

            # Track insertions to apply
            insertions: list[tuple[int, list[str]]] = []

            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "insert":
                    insertions.append((i1, after_lines[j1:j2]))
                elif tag == "replace":
                    # For replacements, add conflict markers
                    if i1 < len(result_lines):
                        marker = [
                            f"<<<<<<< {change.tool}\n",
                            *after_lines[j1:j2],
                            "=======\n",
                            *base_lines[i1:i2],
                            ">>>>>>> original\n",
                        ]
                        result_lines[i1:i2] = marker

            # Apply insertions (in reverse order to preserve indices)
            for idx, new_lines in reversed(insertions):
                result_lines[idx:idx] = new_lines

        return "".join(result_lines)

    def _smart_merge(self, conflict: FileConflict) -> str:
        """Attempt intelligent merge based on change semantics."""
        actual_changes = [c for c in conflict.changes if c.has_changes]
        if len(actual_changes) < 2:
            return actual_changes[0].after.content if actual_changes else ""

        # Try 3-way merge using git merge-file if available
        try:
            return self._git_merge_file(conflict)
        except Exception:
            pass

        # Fall back to union merge
        return self._merge_union(conflict)

    def _git_merge_file(self, conflict: FileConflict) -> str:
        """Use git merge-file for 3-way merge."""
        import tempfile

        actual_changes = [c for c in conflict.changes if c.has_changes]
        if len(actual_changes) < 2:
            raise ValueError("Need at least 2 changes for merge")

        # Create temp files for merge
        with tempfile.NamedTemporaryFile(mode="w", suffix=".base", delete=False) as base_f:
            base_f.write(actual_changes[0].before.content)
            base_path = base_f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ours", delete=False) as ours_f:
            ours_f.write(actual_changes[0].after.content)
            ours_path = ours_f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".theirs", delete=False) as theirs_f:
            theirs_f.write(actual_changes[1].after.content)
            theirs_path = theirs_f.name

        try:
            result = subprocess.run(
                ["git", "merge-file", "-p", ours_path, base_path, theirs_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout
        finally:
            # Clean up temp files
            for p in [base_path, ours_path, theirs_path]:
                Path(p).unlink(missing_ok=True)

    def apply_merged_changes(
        self,
        result: AggregationResult,
        dry_run: bool = False,
    ) -> dict[Path, bool]:
        """Apply merged changes to the filesystem.

        Args:
            result: AggregationResult from resolve()
            dry_run: If True, don't actually write files

        Returns:
            Dict mapping paths to success status

        """
        applied: dict[Path, bool] = {}

        for path, content in result.merged_changes.items():
            try:
                if not dry_run:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                applied[path] = True
            except Exception as e:
                logger.error(f"Failed to apply changes to {path}: {e}")
                applied[path] = False

        return applied

    def get_summary(self) -> str:
        """Get a human-readable summary of all changes."""
        lines = ["# File Change Summary", ""]

        for tool, changes in self._changes.items():
            lines.append(f"## {tool}")
            if not changes:
                lines.append("  No changes")
                continue

            for change in changes:
                status = "+" if change.is_creation else "-" if change.is_deletion else "M"
                lines.append(f"  {status} {change.path.relative_to(self.working_dir)}")

        conflicts = self.detect_conflicts()
        if conflicts:
            lines.append("")
            lines.append("## Conflicts")
            for conflict in conflicts:
                if conflict.conflict_type != ConflictType.NONE:
                    tools = ", ".join(c.tool for c in conflict.changes)
                    lines.append(f"  ! {conflict.path.relative_to(self.working_dir)}")
                    lines.append(f"    Type: {conflict.conflict_type.value}")
                    lines.append(f"    Tools: {tools}")
                    lines.append(f"    {conflict.description}")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset aggregator state for a new execution cycle."""
        self._snapshots.clear()
        self._changes.clear()
        self._current_snapshot.clear()
