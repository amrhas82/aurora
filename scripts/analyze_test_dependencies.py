#!/usr/bin/env python3
"""
Analyze test file dependencies to determine safe migration order.

This script parses test files to identify import dependencies and generates
a migration plan with batches that respect dependency ordering.

Usage:
    python scripts/analyze_test_dependencies.py                    # Analyze all tests
    python scripts/analyze_test_dependencies.py --files file.txt   # Analyze specific files
    python scripts/analyze_test_dependencies.py --output plan.json # Save to JSON
"""

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TestDependencyAnalyzer:
    """Analyzes dependencies between test files."""

    def __init__(self, test_root: Path):
        """
        Initialize analyzer.

        Args:
            test_root: Root directory containing test files
        """
        self.test_root = test_root
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        self.test_files: Set[str] = set()

    def find_test_files(self) -> List[Path]:
        """Find all test files in the test root."""
        return list(self.test_root.rglob("test_*.py"))

    def extract_imports(self, file_path: Path) -> Set[str]:
        """
        Extract import statements from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Set of imported module names
        """
        imports = set()

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])

        except Exception as e:
            print(f"Error parsing {file_path}: {e}", file=sys.stderr)

        return imports

    def is_test_module_import(self, import_name: str) -> bool:
        """
        Check if an import is from the test directory.

        Args:
            import_name: Name of imported module

        Returns:
            True if import is from tests directory
        """
        # Check if import refers to a test file
        if import_name.startswith("tests."):
            return True
        if import_name in ["conftest", "fixtures", "helpers"]:
            return True
        return False

    def build_dependency_graph(self, files: List[Path]) -> None:
        """
        Build dependency graph for given test files.

        Args:
            files: List of test file paths
        """
        # Track all test files
        for file_path in files:
            rel_path = str(file_path.relative_to(self.test_root))
            self.test_files.add(rel_path)

        # Build dependencies
        for file_path in files:
            rel_path = str(file_path.relative_to(self.test_root))
            imports = self.extract_imports(file_path)

            # Check for test module imports
            for imp in imports:
                if self.is_test_module_import(imp):
                    # Add to dependencies
                    self.dependencies[rel_path].add(imp)
                    self.reverse_deps[imp].add(rel_path)

    def detect_circular_dependencies(self) -> List[Tuple[str, str]]:
        """
        Detect circular dependencies in the dependency graph.

        Returns:
            List of (file1, file2) tuples representing circular deps
        """
        circular = []
        visited = set()

        def dfs(node: str, path: Set[str]) -> None:
            if node in path:
                # Found cycle
                circular.append((node, node))
                return

            if node in visited:
                return

            visited.add(node)
            path.add(node)

            for dep in self.dependencies.get(node, []):
                if dep in self.test_files:
                    dfs(dep, path.copy())

            path.remove(node)

        for test_file in self.test_files:
            dfs(test_file, set())

        return circular

    def generate_migration_batches(self, files_to_move: List[str]) -> List[List[str]]:
        """
        Generate migration batches that respect dependencies.

        Files with no dependencies are moved first, followed by files
        that only depend on already-moved files.

        Args:
            files_to_move: List of test files to migrate

        Returns:
            List of batches (each batch is a list of files)
        """
        batches = []
        remaining = set(files_to_move)
        moved = set()

        while remaining:
            # Find files with no unmet dependencies
            batch = []
            for file in remaining:
                deps = self.dependencies.get(file, set())
                # Filter to test file dependencies
                test_deps = {d for d in deps if d in self.test_files}
                # Check if all dependencies are already moved
                unmet_deps = test_deps - moved
                if not unmet_deps:
                    batch.append(file)

            if not batch:
                # Circular dependency or all remaining files have unmet deps
                # Move them all together (risky but necessary)
                batch = list(remaining)
                print(
                    f"Warning: Batch {len(batches) + 1} may have circular dependencies",
                    file=sys.stderr
                )

            batches.append(sorted(batch))
            for file in batch:
                remaining.remove(file)
                moved.add(file)

        return batches

    def analyze(self, files_to_analyze: List[str] = None) -> Dict:
        """
        Perform complete dependency analysis.

        Args:
            files_to_analyze: Specific files to analyze (default: all test files)

        Returns:
            Analysis results as dictionary
        """
        # Find all test files
        all_test_files = self.find_test_files()

        # Build dependency graph
        self.build_dependency_graph(all_test_files)

        # Detect circular dependencies
        circular = self.detect_circular_dependencies()

        # Generate migration batches
        if files_to_analyze:
            batches = self.generate_migration_batches(files_to_analyze)
        else:
            batches = []

        return {
            "total_test_files": len(self.test_files),
            "files_analyzed": len(files_to_analyze) if files_to_analyze else 0,
            "circular_dependencies": len(circular),
            "circular_details": [{"file1": c[0], "file2": c[1]} for c in circular],
            "migration_batches": batches,
            "batch_count": len(batches),
            "dependencies": {
                file: list(deps) for file, deps in self.dependencies.items()
            },
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze test file dependencies for migration planning"
    )
    parser.add_argument(
        "--test-root",
        type=Path,
        default=Path("tests"),
        help="Root directory containing test files (default: tests/)",
    )
    parser.add_argument(
        "--files",
        type=Path,
        help="File containing list of test files to analyze (one per line)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    args = parser.parse_args()

    if not args.test_root.exists():
        print(f"Error: Test root {args.test_root} does not exist", file=sys.stderr)
        sys.exit(1)

    # Read files to analyze
    files_to_analyze = None
    if args.files:
        if not args.files.exists():
            print(f"Error: File list {args.files} does not exist", file=sys.stderr)
            sys.exit(1)
        files_to_analyze = args.files.read_text().strip().split('\n')
        files_to_analyze = [f.strip() for f in files_to_analyze if f.strip()]

    # Perform analysis
    analyzer = TestDependencyAnalyzer(args.test_root)
    results = analyzer.analyze(files_to_analyze)

    # Output results
    output_json = json.dumps(results, indent=2)

    if args.output:
        args.output.write_text(output_json)
        print(f"Analysis saved to {args.output}")
    else:
        print(output_json)

    # Print summary
    print(f"\n{'=' * 70}", file=sys.stderr)
    print("Dependency Analysis Summary", file=sys.stderr)
    print(f"{'=' * 70}", file=sys.stderr)
    print(f"Total test files: {results['total_test_files']}", file=sys.stderr)
    if files_to_analyze:
        print(f"Files to migrate: {results['files_analyzed']}", file=sys.stderr)
        print(f"Migration batches: {results['batch_count']}", file=sys.stderr)
    if results['circular_dependencies'] > 0:
        print(f"⚠️  Circular dependencies detected: {results['circular_dependencies']}", file=sys.stderr)
    else:
        print("✓ No circular dependencies detected", file=sys.stderr)
    print(f"{'=' * 70}", file=sys.stderr)


if __name__ == "__main__":
    main()
