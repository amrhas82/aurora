#!/usr/bin/env python3
"""
Revert __init__.py imports back to old paths to avoid circular dependencies.

This script reverts imports in package __init__.py files from:
    from aurora.core.store import SQLiteStore
back to:
    from aurora_core.store import SQLiteStore

This is necessary to avoid circular dependencies during namespace package initialization.
"""

import re
from pathlib import Path

# Mapping of new namespace paths back to old package names
REVERSE_MAPPINGS = {
    "aurora.core": "aurora_core",
    "aurora.context_code": "aurora_context_code",
    "aurora.soar": "aurora_soar",
    "aurora.reasoning": "aurora_reasoning",
    "aurora.cli": "aurora_cli",
    "aurora.testing": "aurora_testing",
}


def revert_import_line(line: str) -> str:
    """Revert a single line from new namespace import to old package import."""
    for new_name, old_name in REVERSE_MAPPINGS.items():
        # Pattern: from aurora.core.module import ...
        pattern = re.compile(rf'\bfrom\s+{re.escape(new_name)}(\.|[^\w])')
        if pattern.search(line):
            line = pattern.sub(f'from {old_name}\\1', line)

        # Pattern: import aurora.core.module
        pattern2 = re.compile(rf'\bimport\s+{re.escape(new_name)}(\.|[^\w])')
        if pattern2.search(line):
            line = pattern2.sub(f'import {old_name}\\1', line)

    return line


def revert_init_file(file_path: Path) -> int:
    """Revert imports in an __init__.py file."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.splitlines(keepends=True)

    new_lines = []
    modified_count = 0

    for line in lines:
        new_line = revert_import_line(line)
        new_lines.append(new_line)
        if new_line != line:
            modified_count += 1

    if modified_count > 0:
        file_path.write_text(''.join(new_lines), encoding='utf-8')
        print(f"✓ {file_path}: {modified_count} lines reverted")

    return modified_count


def main():
    """Find and revert all __init__.py files in packages/*/src."""
    root = Path("/home/hamr/PycharmProjects/aurora")
    packages_dir = root / "packages"

    init_files = list(packages_dir.rglob("src/**/__init__.py"))
    print(f"Found {len(init_files)} __init__.py files")

    total_modified = 0
    for file_path in init_files:
        count = revert_init_file(file_path)
        total_modified += count

    print(f"\nTotal: {total_modified} lines reverted across all __init__.py files")


if __name__ == "__main__":
    main()
