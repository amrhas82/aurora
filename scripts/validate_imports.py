#!/usr/bin/env python3
"""
Import validation script for pre-commit hook.

Detects old aurora.* import patterns and enforces new aurora_* package naming.

Usage:
    # As pre-commit hook (validates staged files)
    python scripts/validate_imports.py

    # Validate specific files
    python scripts/validate_imports.py file1.py file2.py

    # Validate directory
    python scripts/validate_imports.py --path tests/

Exit codes:
    0 - All imports valid
    1 - Invalid import patterns found
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Old patterns that should be migrated to new package names
OLD_IMPORT_PATTERNS = [
    (r"from aurora\.memory", 'Use "from aurora_memory" instead of "from aurora.memory"'),
    (r"from aurora\.planning", 'Use "from aurora_planning" instead of "from aurora.planning"'),
    (r"from aurora\.cli", 'Use "from aurora_cli" instead of "from aurora.cli"'),
    (r"from aurora\.core", 'Use "from aurora_core" instead of "from aurora.core"'),
    (r"from aurora\.reasoning", 'Use "from aurora_reasoning" instead of "from aurora.reasoning"'),
    (
        r"from aurora\.context_code",
        'Use "from aurora_context_code" instead of "from aurora.context_code"',
    ),
    (r"from aurora\.soar", 'Use "from aurora_soar" instead of "from aurora.soar"'),
    (r"import aurora\.memory", 'Use "import aurora_memory" instead of "import aurora.memory"'),
    (
        r"import aurora\.planning",
        'Use "import aurora_planning" instead of "import aurora.planning"',
    ),
    (r"import aurora\.cli", 'Use "import aurora_cli" instead of "import aurora.cli"'),
    (r"import aurora\.core", 'Use "import aurora_core" instead of "import aurora.core"'),
    (
        r"import aurora\.reasoning",
        'Use "import aurora_reasoning" instead of "import aurora.reasoning"',
    ),
    (
        r"import aurora\.context_code",
        'Use "import aurora_context_code" instead of "import aurora.context_code"',
    ),
    (r"import aurora\.soar", 'Use "import aurora_soar" instead of "import aurora.soar"'),
]


def validate_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Validate imports in a single file.

    Args:
        filepath: Path to the file to validate

    Returns:
        List of (line_number, line_content, error_message) tuples for violations
    """
    violations = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, IOError):
        # Skip binary files or files that can't be read
        return violations

    for line_num, line in enumerate(lines, start=1):
        line_stripped = line.strip()

        # Skip comments and docstrings
        if line_stripped.startswith("#"):
            continue

        # Check each old pattern
        for pattern, message in OLD_IMPORT_PATTERNS:
            if re.search(pattern, line):
                violations.append((line_num, line.rstrip(), message))
                break  # Only report first violation per line

    return violations


def get_staged_python_files() -> List[Path]:
    """
    Get list of Python files staged for commit.

    Returns:
        List of Path objects for staged .py files
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )

        files = []
        for line in result.stdout.strip().split("\n"):
            if line and line.endswith(".py"):
                path = Path(line)
                if path.exists():
                    files.append(path)

        return files
    except subprocess.CalledProcessError:
        # Not in a git repo or git not available
        return []


def find_python_files(path: Path) -> List[Path]:
    """
    Recursively find all Python files in a directory.

    Args:
        path: Directory path to search

    Returns:
        List of Path objects for .py files
    """
    if path.is_file():
        return [path] if path.suffix == ".py" else []

    return list(path.rglob("*.py"))


def main():
    parser = argparse.ArgumentParser(
        description="Validate import patterns in Python files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate staged files (pre-commit hook)
  python scripts/validate_imports.py

  # Validate specific files
  python scripts/validate_imports.py tests/unit/test_memory.py

  # Validate directory
  python scripts/validate_imports.py --path tests/

  # Check all Python files in project
  python scripts/validate_imports.py --path .
        """,
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="Specific files to validate (if not using --path or pre-commit mode)",
    )

    parser.add_argument("--path", type=Path, help="Directory path to recursively validate")

    args = parser.parse_args()

    # Determine which files to validate
    if args.path:
        # Validate all Python files in directory
        files = find_python_files(args.path)
        if not files:
            print(f"No Python files found in {args.path}")
            return 0
    elif args.files:
        # Validate specific files
        files = [Path(f) for f in args.files]
    else:
        # Pre-commit mode: validate staged files
        files = get_staged_python_files()
        if not files:
            # No Python files staged, nothing to validate
            return 0

    # Validate each file
    has_violations = False
    total_violations = 0

    for filepath in files:
        violations = validate_file(filepath)

        if violations:
            has_violations = True
            total_violations += len(violations)

            print(f"\n❌ {filepath}")
            print("=" * 80)

            for line_num, line_content, error_message in violations:
                print(f"  Line {line_num}: {error_message}")
                print(f"    {line_content}")

    # Summary
    if has_violations:
        print("\n" + "=" * 80)
        print(
            f"❌ FAILED: Found {total_violations} invalid import(s) in {len([f for f in files if validate_file(f)])} file(s)"
        )
        print("\nCorrect import patterns:")
        print("  from aurora_memory import ...")
        print("  from aurora_planning import ...")
        print("  from aurora_cli import ...")
        print("  import aurora_memory")
        print("  import aurora_planning")
        print("\nTo fix automatically, run:")
        print("  python scripts/migrate_imports.py --path <file_or_directory>")
        return 1
    else:
        if args.path or args.files:
            print(f"✅ All imports valid ({len(files)} file(s) checked)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
