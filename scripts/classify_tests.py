#!/usr/bin/env python3
"""Detect misclassified tests and suggest correct classification.

This script analyzes test files using heuristics to determine if they're
correctly classified as unit/integration/e2e tests based on their location
and implementation characteristics.

Usage:
    python scripts/classify_tests.py                    # Analyze all tests
    python scripts/classify_tests.py --path tests/unit  # Analyze specific directory
    python scripts/classify_tests.py --output report.txt # Save report
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestClassification:
    """Result of test classification analysis."""

    file_path: str
    current_location: str  # unit, integration, or e2e
    suggested_location: str  # unit, integration, or e2e
    confidence: str  # high, medium, low
    reasons: list[str]
    heuristics_matched: list[str]


class TestClassifier:
    """Classifies tests based on their characteristics."""

    def __init__(self, test_root: Path):
        """Initialize classifier.

        Args:
            test_root: Root directory containing test files
        """
        self.test_root = test_root

    def find_test_files(self, path: Path = None) -> list[Path]:
        """Find all test files in the given path."""
        search_path = path or self.test_root
        return list(search_path.rglob("test_*.py"))

    def get_current_location(self, file_path: Path) -> str:
        """Determine current test location based on directory.

        Args:
            file_path: Path to test file

        Returns:
            'unit', 'integration', 'e2e', or 'unknown'
        """
        rel_path = file_path.relative_to(self.test_root)
        parts = rel_path.parts

        if parts[0] == "unit":
            return "unit"
        elif parts[0] == "integration":
            return "integration"
        elif parts[0] == "e2e":
            return "e2e"
        else:
            return "unknown"

    def analyze_file_content(self, file_path: Path) -> dict[str, any]:
        """Analyze file content for classification heuristics.

        Args:
            file_path: Path to test file

        Returns:
            Dictionary with analysis results
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            return {}

        analysis = {
            "uses_subprocess": False,
            "uses_sqlite_store": False,
            "uses_tmp_path": False,
            "uses_real_cli": False,
            "has_integration_docstring": False,
            "has_e2e_docstring": False,
            "has_mock": False,
            "imports_unittest_mock": False,
            "multi_step_workflow": False,
            "uses_real_database": False,
            "test_count": 0,
            "avg_test_length": 0,
        }

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(file_path))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}", file=sys.stderr)
            return analysis

        # Analyze imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "subprocess" in alias.name:
                        analysis["uses_subprocess"] = True
                    if "mock" in alias.name.lower():
                        analysis["has_mock"] = True
                        analysis["imports_unittest_mock"] = True

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if "subprocess" in node.module:
                        analysis["uses_subprocess"] = True
                    if "mock" in node.module.lower():
                        analysis["has_mock"] = True
                        analysis["imports_unittest_mock"] = True

        # Content-based analysis
        if "subprocess.run" in content or "subprocess.Popen" in content:
            analysis["uses_subprocess"] = True

        if "SQLiteStore(" in content and "Mock" not in content:
            analysis["uses_sqlite_store"] = True

        if "tmp_path" in content:
            analysis["uses_tmp_path"] = True

        # Check for CLI usage
        cli_patterns = [
            r'subprocess\.run\(\["aur"',
            r'subprocess\.run\(\["aurora"',
            r"run_cli_command\(",
        ]
        for pattern in cli_patterns:
            if re.search(pattern, content):
                analysis["uses_real_cli"] = True
                break

        # Check docstrings
        if re.search(r'""".*[Ii]ntegration.*"""', content, re.DOTALL):
            analysis["has_integration_docstring"] = True
        if re.search(r'""".*[Ee]2[Ee].*"""', content, re.DOTALL):
            analysis["has_e2e_docstring"] = True
        if re.search(r'""".*[Ee]nd-to-[Ee]nd.*"""', content, re.DOTALL):
            analysis["has_e2e_docstring"] = True

        # Check for multi-step workflow (heuristic: multiple subprocess calls)
        subprocess_count = content.count("subprocess.run")
        if subprocess_count >= 3:
            analysis["multi_step_workflow"] = True

        # Check for real database usage
        if "db_path" in content and "tmp_path" in content:
            analysis["uses_real_database"] = True

        # Count tests
        test_functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]
        analysis["test_count"] = len(test_functions)

        # Calculate average test length
        if test_functions:
            total_lines = sum(len(ast.unparse(func).split("\n")) for func in test_functions)
            analysis["avg_test_length"] = total_lines // len(test_functions)

        return analysis

    def classify_test(self, file_path: Path) -> TestClassification:
        """Classify a test file.

        Args:
            file_path: Path to test file

        Returns:
            TestClassification with suggested location and reasons
        """
        current_location = self.get_current_location(file_path)
        analysis = self.analyze_file_content(file_path)

        # Score system for classification
        unit_score = 0
        integration_score = 0
        e2e_score = 0

        reasons = []
        heuristics = []

        # E2E heuristics (strongest signals)
        if analysis.get("uses_real_cli"):
            e2e_score += 10
            reasons.append("Uses real CLI commands (subprocess with 'aur')")
            heuristics.append("real_cli")

        if analysis.get("multi_step_workflow"):
            e2e_score += 8
            reasons.append("Multi-step workflow (3+ subprocess calls)")
            heuristics.append("multi_step_workflow")

        if analysis.get("has_e2e_docstring"):
            e2e_score += 5
            reasons.append("Docstring mentions 'e2e' or 'end-to-end'")
            heuristics.append("e2e_docstring")

        # Integration heuristics
        if analysis.get("uses_subprocess") and not analysis.get("uses_real_cli"):
            integration_score += 7
            reasons.append("Uses subprocess (but not for CLI)")
            heuristics.append("subprocess")

        if analysis.get("uses_sqlite_store"):
            integration_score += 6
            reasons.append("Uses SQLiteStore with real database")
            heuristics.append("sqlite_store")

        if analysis.get("uses_tmp_path") and not analysis.get("uses_real_cli"):
            integration_score += 4
            reasons.append("Uses tmp_path for filesystem operations")
            heuristics.append("tmp_path")

        if analysis.get("has_integration_docstring"):
            integration_score += 5
            reasons.append("Docstring mentions 'integration'")
            heuristics.append("integration_docstring")

        if analysis.get("uses_real_database"):
            integration_score += 6
            reasons.append("Uses real database with tmp_path")
            heuristics.append("real_database")

        # Unit test heuristics
        if analysis.get("imports_unittest_mock") or analysis.get("has_mock"):
            unit_score += 5
            reasons.append("Imports and uses mocks")
            heuristics.append("uses_mocks")

        if analysis.get("avg_test_length", 0) < 15:
            unit_score += 3
            reasons.append(f"Short tests (avg {analysis.get('avg_test_length')} lines)")
            heuristics.append("short_tests")

        # No I/O indicators suggest unit test
        no_io = (
            not analysis.get("uses_subprocess")
            and not analysis.get("uses_sqlite_store")
            and not analysis.get("uses_tmp_path")
        )
        if no_io:
            unit_score += 7
            reasons.append("No I/O operations detected")
            heuristics.append("no_io")

        # Determine suggested location
        scores = {
            "unit": unit_score,
            "integration": integration_score,
            "e2e": e2e_score,
        }
        suggested_location = max(scores, key=scores.get)

        # If all scores are 0, keep current location
        if max(scores.values()) == 0:
            suggested_location = current_location
            reasons.append("No strong indicators, keeping current location")
            heuristics.append("no_indicators")

        # Determine confidence
        max_score = scores[suggested_location]
        second_max = sorted(scores.values())[-2] if len(scores) > 1 else 0
        score_diff = max_score - second_max

        if score_diff >= 10:
            confidence = "high"
        elif score_diff >= 5:
            confidence = "medium"
        else:
            confidence = "low"

        rel_path = str(file_path.relative_to(self.test_root))

        return TestClassification(
            file_path=rel_path,
            current_location=current_location,
            suggested_location=suggested_location,
            confidence=confidence,
            reasons=reasons,
            heuristics_matched=heuristics,
        )

    def classify_all(self, path: Path = None) -> list[TestClassification]:
        """Classify all test files.

        Args:
            path: Optional path to analyze (default: all tests)

        Returns:
            List of TestClassification results
        """
        test_files = self.find_test_files(path)
        results = []

        for file_path in test_files:
            classification = self.classify_test(file_path)
            results.append(classification)

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Classify tests and detect misclassifications")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("tests"),
        help="Path to analyze (default: tests/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--misclassified-only",
        action="store_true",
        help="Only show misclassified tests",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    # Perform classification
    classifier = TestClassifier(Path("tests"))
    results = classifier.classify_all(args.path)

    # Filter if needed
    if args.misclassified_only:
        results = [
            r
            for r in results
            if r.current_location != r.suggested_location and r.current_location != "unknown"
        ]

    # Generate report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("Test Classification Report")
    report_lines.append("=" * 80)
    report_lines.append("")

    misclassified_count = 0
    by_type = {"unit": [], "integration": [], "e2e": []}

    for result in results:
        if (
            result.current_location != result.suggested_location
            and result.current_location != "unknown"
        ):
            misclassified_count += 1

            # Categorize by suggested location
            by_type[result.suggested_location].append(result)

            report_lines.append(f"File: {result.file_path}")
            report_lines.append(f"  Current:   tests/{result.current_location}/")
            report_lines.append(f"  Suggested: tests/{result.suggested_location}/")
            report_lines.append(f"  Confidence: {result.confidence.upper()}")
            report_lines.append("  Reasons:")
            for reason in result.reasons:
                report_lines.append(f"    - {reason}")
            report_lines.append("")

    # Summary
    report_lines.append("=" * 80)
    report_lines.append("Summary")
    report_lines.append("=" * 80)
    report_lines.append(f"Total files analyzed: {len(results)}")
    report_lines.append(f"Misclassified files: {misclassified_count}")
    report_lines.append("")
    report_lines.append("Files needing reclassification:")
    report_lines.append(f"  → Move to tests/unit/: {len(by_type['unit'])} files")
    report_lines.append(f"  → Move to tests/integration/: {len(by_type['integration'])} files")
    report_lines.append(f"  → Move to tests/e2e/: {len(by_type['e2e'])} files")
    report_lines.append("=" * 80)

    report = "\n".join(report_lines)

    # Output
    if args.output:
        args.output.write_text(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
