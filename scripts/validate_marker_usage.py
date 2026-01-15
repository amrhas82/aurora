#!/usr/bin/env python3
"""Validate pytest marker usage in test files.

This script detects redundant markers where the marker duplicates information
already conveyed by the test file's location:
- Tests in tests/unit/ don't need @pytest.mark.unit
- Tests in tests/integration/ don't need @pytest.mark.integration
- Tests in tests/e2e/ don't need @pytest.mark.e2e

Usage:
    python scripts/validate_marker_usage.py              # Check all tests
    python scripts/validate_marker_usage.py --fix        # Remove redundant markers
    python scripts/validate_marker_usage.py tests/unit/  # Check specific directory
"""

import argparse
import re
import sys
from pathlib import Path


def find_redundant_markers(file_path: Path) -> list[tuple[int, str, str]]:
    """Find redundant markers in a test file.

    Args:
        file_path: Path to the test file

    Returns:
        List of tuples: (line_number, line_content, marker_name)
    """
    redundant = []

    # Determine which marker would be redundant based on file location
    redundant_marker = None
    if "/tests/unit/" in str(file_path) or str(file_path).startswith("tests/unit/"):
        redundant_marker = "unit"
    elif "/tests/integration/" in str(file_path) or str(file_path).startswith("tests/integration/"):
        redundant_marker = "integration"
    elif "/tests/e2e/" in str(file_path) or str(file_path).startswith("tests/e2e/"):
        redundant_marker = "e2e"

    if not redundant_marker:
        return redundant

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return redundant

    # Look for @pytest.mark.{redundant_marker}
    pattern = re.compile(rf"@pytest\.mark\.{redundant_marker}\b")

    for line_num, line in enumerate(lines, start=1):
        if pattern.search(line):
            redundant.append((line_num, line.strip(), redundant_marker))

    return redundant


def find_python_test_files(root_path: Path) -> list[Path]:
    """Find all Python test files in the given directory tree."""
    return list(root_path.rglob("test_*.py"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate pytest marker usage and detect redundancies"
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("tests"),
        help="Path to search for test files (default: tests/)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Remove redundant markers (not just report them)",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"{'=' * 70}")
    print("Pytest Marker Redundancy Check")
    print(f"{'=' * 70}")
    print(f"Searching in: {args.path.absolute()}")
    print(f"Mode: {'FIX (will remove)' if args.fix else 'REPORT ONLY'}")
    print()

    # Find all test files
    test_files = find_python_test_files(args.path)
    print(f"Found {len(test_files)} test files")
    print()

    # Check each file
    total_redundant = 0
    files_with_redundant = 0

    for file_path in test_files:
        redundant = find_redundant_markers(file_path)

        if redundant:
            files_with_redundant += 1
            total_redundant += len(redundant)

            print(f"{file_path}")
            for line_num, line, marker in redundant:
                print(f"  Line {line_num}: {line}")
                print(f"    → Redundant @pytest.mark.{marker} (already in {marker}/ directory)")
            print()

    # Summary
    print(f"{'=' * 70}")
    print("Summary")
    print(f"{'=' * 70}")
    print(f"Files checked: {len(test_files)}")
    print(f"Files with redundant markers: {files_with_redundant}")
    print(f"Total redundant markers: {total_redundant}")
    print()

    if total_redundant > 0:
        if args.fix:
            print("FIX mode not yet implemented. Use remove_redundant_markers.py")
            sys.exit(1)
        else:
            print("Run with --fix to remove redundant markers (or use remove_redundant_markers.py)")
            sys.exit(1)  # Exit with error code to use as pre-commit hook
    else:
        print("✓ No redundant markers found")
        sys.exit(0)


if __name__ == "__main__":
    main()
