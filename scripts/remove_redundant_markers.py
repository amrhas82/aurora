#!/usr/bin/env python3
"""
Remove redundant pytest markers from test files.

This script removes markers that are redundant because they duplicate
information already conveyed by the test file's location.

Usage:
    python scripts/remove_redundant_markers.py --dry-run  # Preview changes
    python scripts/remove_redundant_markers.py            # Apply changes
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List


def find_python_test_files(root_path: Path) -> List[Path]:
    """Find all Python test files in the given directory tree."""
    return list(root_path.rglob("test_*.py"))


def remove_redundant_markers_from_file(file_path: Path, dry_run: bool = False) -> tuple[int, int]:
    """
    Remove redundant markers from a single test file.

    Args:
        file_path: Path to the test file
        dry_run: If True, only report changes without modifying file

    Returns:
        Tuple of (lines_removed, lines_modified)
    """
    # Determine which marker would be redundant based on file location
    redundant_marker = None
    if "/tests/unit/" in str(file_path) or str(file_path).startswith("tests/unit/"):
        redundant_marker = "unit"
    elif "/tests/integration/" in str(file_path) or str(file_path).startswith("tests/integration/"):
        redundant_marker = "integration"
    elif "/tests/e2e/" in str(file_path) or str(file_path).startswith("tests/e2e/"):
        redundant_marker = "e2e"

    if not redundant_marker:
        return (0, 0)

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return (0, 0)

    # Pattern for decorator line: @pytest.mark.{marker}
    decorator_pattern = re.compile(rf"^(\s*)@pytest\.mark\.{redundant_marker}\s*$")

    # Pattern for inline references in comments/docstrings (don't remove these)
    comment_pattern = re.compile(r"^\s*(#|\"\"\")")

    new_lines = []
    lines_removed = 0
    lines_modified = 0

    for line in lines:
        # Skip removing from comments and docstrings
        if comment_pattern.match(line):
            new_lines.append(line)
            continue

        # Check if this is a redundant decorator line
        if decorator_pattern.match(line):
            lines_removed += 1
            if dry_run:
                print(f"{file_path}")
                print(f"  - {line.rstrip()}")
            # Don't append this line (effectively removing it)
            continue

        new_lines.append(line)

    if lines_removed > 0:
        lines_modified = lines_removed

        if not dry_run:
            try:
                file_path.write_text("".join(new_lines), encoding="utf-8")
                print(f"✓ {file_path}: {lines_removed} redundant markers removed")
            except Exception as e:
                print(f"Error writing {file_path}: {e}", file=sys.stderr)
                return (0, 0)
        elif dry_run:
            print(f"  [DRY RUN] Would remove {lines_removed} markers from {file_path}")
            print()

    return (lines_removed, lines_modified)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Remove redundant pytest markers from test files")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("tests"),
        help="Path to search for test files (default: tests/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"{'=' * 70}")
    print(f"Remove Redundant Pytest Markers {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'=' * 70}")
    print(f"Searching in: {args.path.absolute()}")
    print()

    # Find all test files
    test_files = find_python_test_files(args.path)
    print(f"Found {len(test_files)} test files")
    print()

    # Process each file
    total_files_modified = 0
    total_lines_removed = 0

    for file_path in test_files:
        lines_removed, lines_modified = remove_redundant_markers_from_file(
            file_path, dry_run=args.dry_run
        )

        if lines_removed > 0:
            total_files_modified += 1
            total_lines_removed += lines_removed

    # Summary
    print()
    print(f"{'=' * 70}")
    print("Summary")
    print(f"{'=' * 70}")
    print(f"Files processed: {len(test_files)}")
    print(f"Files modified: {total_files_modified}")
    print(f"Markers removed: {total_lines_removed}")

    if args.dry_run:
        print("\nThis was a dry run. No files were modified.")
        print("Run without --dry-run to apply changes.")
    else:
        print("\nMarker removal complete!")

    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
