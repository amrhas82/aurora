#!/usr/bin/env python3
"""
Import Path Migration Script for AURORA v0.2.0

This script migrates import statements from the old package-specific naming
to the new unified namespace:

Old: from aurora_core.store import SQLiteStore
New: from aurora.core.store import SQLiteStore

Old: import aurora_context_code.semantic
New: import aurora.context_code.semantic

Usage:
    python scripts/migrate_imports.py --dry-run  # Preview changes
    python scripts/migrate_imports.py            # Apply changes
    python scripts/migrate_imports.py --path packages/cli  # Specific directory
"""

import argparse
import re
import sys
from pathlib import Path


# Deprecated typing imports - use lowercase


# Mapping of old package names to new namespace paths
PACKAGE_MAPPINGS = {
    "aurora_core": "aurora.core",
    "aurora_context_code": "aurora.context_code",
    "aurora_soar": "aurora.soar",
    "aurora_reasoning": "aurora.reasoning",
    "aurora_cli": "aurora.cli",
    "aurora_testing": "aurora.testing",
}


def find_python_files(root_path: Path) -> list[Path]:
    """Find all Python files in the given directory tree."""
    return list(root_path.rglob("*.py"))


def migrate_import_line(line: str) -> tuple[str, bool]:
    """
    Migrate a single line of code, replacing old import patterns.

    Returns:
        Tuple of (migrated_line, was_modified)
    """
    original = line
    modified = False

    for old_name, new_name in PACKAGE_MAPPINGS.items():
        # Pattern 1: from aurora_core.module import ...
        # Replace with: from aurora.core.module import ...
        pattern1 = re.compile(rf'\bfrom\s+{re.escape(old_name)}(\.|[^\w])')
        if pattern1.search(line):
            line = pattern1.sub(f'from {new_name}\\1', line)
            modified = True

        # Pattern 2: import aurora_core.module
        # Replace with: import aurora.core.module
        pattern2 = re.compile(rf'\bimport\s+{re.escape(old_name)}(\.|[^\w])')
        if pattern2.search(line):
            line = pattern2.sub(f'import {new_name}\\1', line)
            modified = True

        # Pattern 3: import aurora_core (standalone package import)
        # Replace with: import aurora.core
        pattern3 = re.compile(rf'\bimport\s+{re.escape(old_name)}(?:\s+as\s+|\s*,|\s*$)')
        if pattern3.search(line):
            line = line.replace(old_name, new_name)
            modified = True

        # Pattern 4: In comments or docstrings (informational only)
        # Example: "Uses aurora_core.store" -> "Uses aurora.core.store"
        if old_name in line and not modified:
            # Only replace in comments and docstrings
            if line.strip().startswith('#') or '"""' in original or "'''" in original:
                line = line.replace(old_name, new_name)
                modified = True

    return line, modified


def migrate_file(file_path: Path, dry_run: bool = False) -> dict[str, int]:
    """
    Migrate imports in a single file.

    Returns:
        Dictionary with statistics: lines_modified, total_lines
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.splitlines(keepends=True)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return {"lines_modified": 0, "total_lines": 0, "error": True}

    new_lines = []
    modified_count = 0

    for line_num, line in enumerate(lines, start=1):
        new_line, was_modified = migrate_import_line(line)
        new_lines.append(new_line)

        if was_modified:
            modified_count += 1
            if dry_run:
                print(f"{file_path}:{line_num}")
                print(f"  - {line.rstrip()}")
                print(f"  + {new_line.rstrip()}")

    if modified_count > 0 and not dry_run:
        try:
            file_path.write_text(''.join(new_lines), encoding='utf-8')
            print(f"✓ {file_path}: {modified_count} lines migrated")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return {"lines_modified": 0, "total_lines": len(lines), "error": True}
    elif modified_count > 0 and dry_run:
        print(f"[DRY RUN] Would modify {modified_count} lines in {file_path}")

    return {
        "lines_modified": modified_count,
        "total_lines": len(lines),
        "error": False,
    }


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate AURORA imports from old package names to new namespace"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Root path to search for Python files (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        default=True,
        help="Include test files in migration (default: True)",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"{'=' * 70}")
    print(f"AURORA Import Path Migration {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'=' * 70}")
    print(f"Searching in: {args.path.absolute()}")
    print(f"Include tests: {args.include_tests}")
    print()

    # Find all Python files
    python_files = find_python_files(args.path)

    if not args.include_tests:
        python_files = [f for f in python_files if 'test' not in str(f)]

    print(f"Found {len(python_files)} Python files")
    print()

    # Migrate each file
    total_files_modified = 0
    total_lines_modified = 0
    errors = []

    for file_path in python_files:
        result = migrate_file(file_path, dry_run=args.dry_run)

        if result.get("error"):
            errors.append(file_path)

        if result["lines_modified"] > 0:
            total_files_modified += 1
            total_lines_modified += result["lines_modified"]

    # Summary
    print()
    print(f"{'=' * 70}")
    print("Migration Summary")
    print(f"{'=' * 70}")
    print(f"Files processed: {len(python_files)}")
    print(f"Files modified: {total_files_modified}")
    print(f"Lines modified: {total_lines_modified}")

    if errors:
        print(f"\nErrors encountered in {len(errors)} files:")
        for error_file in errors:
            print(f"  - {error_file}")
        sys.exit(1)

    if args.dry_run:
        print("\nThis was a dry run. No files were modified.")
        print("Run without --dry-run to apply changes.")
    else:
        print("\nMigration complete!")

    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
