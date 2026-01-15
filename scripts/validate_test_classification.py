#!/usr/bin/env python3
"""Test classification validation script for pre-commit hook.

Detects misclassified tests (integration/e2e tests in unit/ directory, etc.)
based on objective heuristics.

Usage:
    # As pre-commit hook (validates staged files)
    python scripts/validate_test_classification.py

    # Validate specific files
    python scripts/validate_test_classification.py tests/unit/test_foo.py

    # Validate directory
    python scripts/validate_test_classification.py --path tests/

Exit codes:
    0 - All tests properly classified
    1 - Misclassified tests found
"""

import argparse
import re
import sys
from pathlib import Path

# Heuristics for detecting integration tests
INTEGRATION_INDICATORS = [
    # subprocess usage (real process execution)
    (r"subprocess\.run\(", "Uses subprocess.run() - likely integration test"),
    (r"subprocess\.Popen\(", "Uses subprocess.Popen() - likely integration test"),
    (r"subprocess\.call\(", "Uses subprocess.call() - likely integration test"),
    (r"subprocess\.check_output\(", "Uses subprocess.check_output() - likely integration test"),
    # Real database usage (not mocked)
    (r"SQLiteStore\([^)]*\)", "Uses real SQLiteStore - likely integration test"),
    (r"sqlite3\.connect\(", "Uses real SQLite connection - likely integration test"),
    # Docstring explicitly says integration
    (r'""".*[Ii]ntegration.*"""', 'Docstring mentions "integration"'),
    (r"'''.*[Ii]ntegration.*'''", 'Docstring mentions "integration"'),
]

# Heuristics for detecting E2E tests
E2E_INDICATORS = [
    # Docstring explicitly says e2e
    (r'""".*[Ee]2[Ee].*"""', 'Docstring mentions "e2e" or "end-to-end"'),
    (r"'''.*[Ee]2[Ee].*'''", 'Docstring mentions "e2e" or "end-to-end"'),
    (r'""".*end.to.end.*"""', 'Docstring mentions "end-to-end"'),
    (r"'''.*end.to.end.*'''", 'Docstring mentions "end-to-end"'),
    # API key usage (external service calls)
    (r"ANTHROPIC_API_KEY", "Uses ANTHROPIC_API_KEY - likely E2E test"),
    (r"os\.environ.*API.*KEY", "Uses API key from environment - likely E2E test"),
    # Real CLI invocation
    (r"CliRunner\(\)\.invoke\(", "Uses Click CliRunner - might be E2E"),
]


class TestClassificationChecker:
    """Checks if test files are properly classified based on their location and content."""

    def __init__(self):
        self.integration_patterns = [(re.compile(p), m) for p, m in INTEGRATION_INDICATORS]
        self.e2e_patterns = [(re.compile(p), m) for p, m in E2E_INDICATORS]

    def check_file(self, filepath: Path) -> list[tuple[str, list[str]]]:
        """Check if a test file is properly classified.

        Args:
            filepath: Path to the test file

        Returns:
            List of (classification, [reasons]) tuples for violations
            Empty list if file is properly classified
        """
        # Determine expected location from content
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []  # Skip files that can't be read

        # Check if file is in tests/ directory
        parts = filepath.parts
        if "tests" not in parts:
            return []  # Not a test file

        # Determine current location
        tests_idx = parts.index("tests")
        if tests_idx + 1 >= len(parts):
            return []  # File directly in tests/

        current_location = parts[tests_idx + 1]  # unit, integration, or e2e

        # Find indicators in content
        integration_reasons = []
        e2e_reasons = []

        for pattern, message in self.integration_patterns:
            if pattern.search(content):
                integration_reasons.append(message)

        for pattern, message in self.e2e_patterns:
            if pattern.search(content):
                e2e_reasons.append(message)

        # Determine violations
        violations = []

        if current_location == "unit":
            # Unit tests should not have integration or e2e indicators
            if e2e_reasons:
                violations.append(("e2e", e2e_reasons))
            elif integration_reasons:
                # Only flag if multiple integration indicators (to avoid false positives)
                if len(integration_reasons) >= 2 or any(
                    "SQLiteStore" in r for r in integration_reasons
                ):
                    violations.append(("integration", integration_reasons))

        elif current_location == "integration":
            # Integration tests should not have e2e indicators
            if e2e_reasons:
                violations.append(("e2e", e2e_reasons))

        # Note: E2E tests can have any indicators, so no checks needed

        return violations

    def check_for_mock_usage(self, filepath: Path) -> bool:
        """Check if file uses mocking (which suggests it should be a unit test).

        Args:
            filepath: Path to the test file

        Returns:
            True if file uses mocks, False otherwise
        """
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            # Check for mock imports and decorators
            mock_patterns = [
                r"from unittest\.mock import",
                r"from unittest import mock",
                r"@mock\.patch",
                r"@patch\(",
                r"Mock\(",
                r"MagicMock\(",
            ]

            for pattern in mock_patterns:
                if re.search(pattern, content):
                    return True

            return False
        except (OSError, UnicodeDecodeError):
            return False


def get_staged_test_files() -> list[Path]:
    """Get list of test files staged for commit.

    Returns:
        List of Path objects for staged test files
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
            if line and line.startswith("tests/") and line.endswith(".py"):
                path = Path(line)
                if path.exists():
                    files.append(path)

        return files
    except subprocess.CalledProcessError:
        return []


def find_test_files(path: Path) -> list[Path]:
    """Recursively find all test files in a directory.

    Args:
        path: Directory path to search

    Returns:
        List of Path objects for test_*.py files
    """
    if path.is_file():
        return [path] if path.name.startswith("test_") and path.suffix == ".py" else []

    test_files = []
    for pattern in ["**/test_*.py", "**/*_test.py"]:
        test_files.extend(path.glob(pattern))

    return test_files


def main():
    parser = argparse.ArgumentParser(
        description="Validate test classification (unit/integration/e2e)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate staged files (pre-commit hook)
  python scripts/validate_test_classification.py

  # Validate specific files
  python scripts/validate_test_classification.py tests/unit/test_memory.py

  # Validate directory
  python scripts/validate_test_classification.py --path tests/

Classification Rules:
  - Unit tests: Single function/class, mocked dependencies, <1s, no I/O
  - Integration tests: Multiple components, may use real SQLiteStore/subprocess, <10s
  - E2E tests: Complete workflows, real APIs/CLI, <60s

Indicators:
  - subprocess.run(), SQLiteStore() without mocks → integration
  - API keys, full CLI workflows → e2e
  - Multiple integration indicators → likely misclassified
        """,
    )

    parser.add_argument("files", nargs="*", help="Specific files to validate")

    parser.add_argument("--path", type=Path, help="Directory path to recursively validate")

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (flag single integration indicators)",
    )

    args = parser.parse_args()

    # Determine which files to validate
    if args.path:
        files = find_test_files(args.path)
        if not files:
            print(f"No test files found in {args.path}")
            return 0
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        # Pre-commit mode
        files = get_staged_test_files()
        if not files:
            return 0

    # Validate each file
    checker = TestClassificationChecker()
    has_violations = False
    total_violations = 0

    for filepath in files:
        violations = checker.check_file(filepath)

        if violations:
            has_violations = True
            total_violations += len(violations)

            print(f"\n⚠️  {filepath}")
            print("=" * 80)

            for suggested_location, reasons in violations:
                print(
                    f"  Should be in tests/{suggested_location}/ (currently in tests/{filepath.parts[filepath.parts.index('tests') + 1]}/)"
                )
                print("  Reasons:")
                for reason in reasons:
                    print(f"    - {reason}")

                # Check if it uses mocks (suggests it's a unit test after all)
                if suggested_location == "integration" and checker.check_for_mock_usage(filepath):
                    print(
                        "  ℹ️  Note: File uses mocks - may be acceptable as unit test with edge case"
                    )

    # Summary
    if has_violations:
        print("\n" + "=" * 80)
        print(f"⚠️  WARNING: Found {total_violations} potentially misclassified test(s)")
        print("\nTest Classification Guidelines:")
        print("  tests/unit/       - Single component, mocked dependencies, <1s")
        print("  tests/integration/- Multiple components, real I/O, <10s")
        print("  tests/e2e/        - Complete workflows, real APIs, <60s")
        print("\nTo reclassify tests, use:")
        print("  git mv tests/unit/test_foo.py tests/integration/test_foo.py")
        print("\nOr see: docs/TESTING.md for classification decision tree")
        return 1
    else:
        if args.path or args.files:
            print(f"✅ All tests properly classified ({len(files)} file(s) checked)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
