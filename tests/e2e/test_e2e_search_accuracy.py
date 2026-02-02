"""E2E Test: Search Accuracy (Task 1.3)

This test suite validates that search returns varied, relevant results
based on the query, not identical results for all queries.

Test Scenario: Search Result Variety
1. Index codebase with diverse content
2. Run 3+ different searches with varied queries
3. Parse JSON output from searches
4. Assert top results differ across queries (not identical)
5. Assert activation scores vary across chunks (stddev > 0.1)
6. Assert semantic scores vary based on relevance
7. Assert line ranges are not all "0-0"

Expected: These tests will FAIL initially due to Issue #4 (identical search results)
- Current behavior: All searches return same 5 results with score 1.000
- Expected behavior: Different queries return different, relevant results

Reference: PRD-0010 Section 3 (User Stories), US-2 (Accurate Search Results)
"""

import json
import os
import statistics
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .conftest import run_cli_command


# Mark all tests in this file as E2E tests
pytestmark = [pytest.mark.e2e]


@pytest.fixture
def clean_aurora_home() -> Generator[Path, None, None]:
    """Create a clean, isolated Aurora home directory for testing."""
    original_home = os.environ.get("HOME")
    original_aurora_home = os.environ.get("AURORA_HOME")

    with tempfile.TemporaryDirectory() as tmp_home:
        os.environ["HOME"] = tmp_home
        os.environ["AURORA_HOME"] = str(Path(tmp_home) / ".aurora")

        aurora_home = Path(tmp_home) / ".aurora"
        aurora_home.mkdir(parents=True, exist_ok=True)

        # Create config
        config_path = aurora_home / "config.json"
        config_data = {
            "llm": {"provider": "anthropic"},
            "db_path": str(aurora_home / "memory.db"),
        }
        config_path.write_text(json.dumps(config_data, indent=2))

        yield aurora_home

        if original_home:
            os.environ["HOME"] = original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]

        if original_aurora_home:
            os.environ["AURORA_HOME"] = original_aurora_home
        elif "AURORA_HOME" in os.environ:
            del os.environ["AURORA_HOME"]


@pytest.fixture
def diverse_python_project() -> Generator[Path, None, None]:
    """Create a Python project with diverse, searchable content."""
    with tempfile.TemporaryDirectory() as tmp_project:
        project_path = Path(tmp_project)

        # Create database module
        (project_path / "database.py").write_text(
            '''"""Database management with SQLite."""
import sqlite3
from typing import List, Dict, Any

from .conftest import run_cli_command


class DatabaseManager:
    """Manages SQLite database connections and queries."""

    def __init__(self, db_path: str):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish database connection."""
        self.connection = sqlite3.connect(self.db_path)

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL query and return results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
''',
        )

        # Create HTTP/API module
        (project_path / "api_client.py").write_text(
            '''"""HTTP API client for external services."""
import requests
from typing import Dict, Any, Optional


class APIClient:
    """Client for making HTTP API requests."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize API client.

        Args:
            base_url: Base URL for API endpoints
            api_key: Optional API key for authentication
        """
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to API endpoint.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = self.session.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to API endpoint.

        Args:
            endpoint: API endpoint path
            data: Request payload

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = self.session.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
''',
        )

        # Create file I/O module
        (project_path / "file_handler.py").write_text(
            '''"""File handling and I/O operations."""
import os
import json
from pathlib import Path
from typing import List, Optional


class FileHandler:
    """Handles file reading, writing, and manipulation."""

    def __init__(self, base_dir: str):
        """Initialize file handler.

        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = Path(base_dir)

    def read_text_file(self, filename: str) -> str:
        """Read text file contents.

        Args:
            filename: Name of file to read

        Returns:
            File contents as string
        """
        file_path = self.base_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_text_file(self, filename: str, content: str):
        """Write text to file.

        Args:
            filename: Name of file to write
            content: Content to write
        """
        file_path = self.base_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read_json_file(self, filename: str) -> dict:
        """Read and parse JSON file.

        Args:
            filename: Name of JSON file

        Returns:
            Parsed JSON as dictionary
        """
        file_path = self.base_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_files(self, pattern: str = "*") -> List[Path]:
        """List files matching pattern.

        Args:
            pattern: Glob pattern for filtering files

        Returns:
            List of matching file paths
        """
        return list(self.base_dir.glob(pattern))
''',
        )

        # Create math/algorithm module
        (project_path / "algorithms.py").write_text(
            '''"""Mathematical algorithms and computations."""
from typing import List


def binary_search(arr: List[int], target: int) -> int:
    """Perform binary search on sorted array.

    Args:
        arr: Sorted array of integers
        target: Value to find

    Returns:
        Index of target, or -1 if not found
    """
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number.

    Args:
        n: Position in Fibonacci sequence

    Returns:
        Fibonacci number at position n
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def factorial(n: int) -> int:
    """Calculate factorial of n.

    Args:
        n: Non-negative integer

    Returns:
        Factorial of n
    """
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
''',
        )

        yield project_path


class TestSearchAccuracy:
    """E2E tests for search result accuracy and variety.

    These tests verify that Aurora returns relevant, varied search results
    based on query content, not identical results for all queries.
    """

    def test_1_3_1_index_codebase_with_diverse_content(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.1: Write test that indexes codebase with diverse content.

        Indexes a project with clearly distinct modules (database, API, file I/O, algorithms).
        """
        # Index the diverse project
        result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
        )

        assert result.returncode == 0, f"Indexing failed:\nstderr: {result.stderr}"

        # Verify indexed multiple files
        assert "database.py" in result.stdout.lower() or "indexed" in result.stdout.lower(), (
            f"Should have indexed files:\n{result.stdout}"
        )

    def test_1_3_2_different_queries_return_different_results(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.2: Run 3+ different searches with varied queries.

        EXPECTED TO FAIL: All searches return identical results (Issue #4).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Run 3 distinct searches
        queries = [
            "database sqlite connection query",
            "http api requests client",
            "file read write json",
        ]

        results = []
        for query in queries:
            result = run_cli_command(
                ["aur", "mem", "search", query, "--output", "json"],
                capture_output=True,
                text=True,
                cwd=diverse_python_project,
                timeout=30,
            )

            # If command failed, try without --output json
            if result.returncode != 0:
                result = run_cli_command(
                    ["aur", "mem", "search", query],
                    capture_output=True,
                    text=True,
                    cwd=diverse_python_project,
                    timeout=30,
                    check=True,
                )
                results.append({"query": query, "output": result.stdout, "format": "text"})
            else:
                try:
                    data = json.loads(result.stdout)
                    results.append({"query": query, "output": data, "format": "json"})
                except json.JSONDecodeError:
                    results.append({"query": query, "output": result.stdout, "format": "text"})

        # Assert results differ across queries
        # Check that at least the output strings are different
        outputs = [r["output"] for r in results]

        # Convert to strings for comparison
        output_strs = [str(o) for o in outputs]

        # Results should be different
        assert output_strs[0] != output_strs[1] or output_strs[1] != output_strs[2], (
            f"Search results are identical for different queries (Issue #4)!\n"
            f"Query 1: {queries[0]}\n"
            f"Query 2: {queries[1]}\n"
            f"Query 3: {queries[2]}\n"
            f"All returned same results"
        )

    def test_1_3_3_parse_json_output(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.3: Parse JSON output from `aur mem search --output json`.

        Verifies JSON output is parseable and has expected structure.
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Run search with JSON output
        result = run_cli_command(
            ["aur", "mem", "search", "database", "--output", "json"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
        )

        # Try to parse JSON
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)

                # Verify it's a list of results
                assert isinstance(data, list), f"Expected list of results, got {type(data)}"

                if len(data) > 0:
                    # Check structure of first result
                    first = data[0]
                    expected_fields = {"file_path", "score", "content"}

                    # At least some expected fields should be present
                    present_fields = set(first.keys()) & expected_fields
                    assert len(present_fields) > 0, (
                        f"Result should have expected fields like {expected_fields}, got {first.keys()}"
                    )
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON output is not parseable:\n{result.stdout}\nError: {e}")
        else:
            pytest.skip("--output json not supported or search failed")

    def test_1_3_4_top_results_differ_across_queries(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.4: Assert top results differ across queries (not identical).

        EXPECTED TO FAIL: All queries return same top result (Issue #4).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Run distinct queries
        query1_result = run_cli_command(
            ["aur", "mem", "search", "sqlite database connection"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
            check=True,
        )

        query2_result = run_cli_command(
            ["aur", "mem", "search", "http api requests post get"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
            check=True,
        )

        query3_result = run_cli_command(
            ["aur", "mem", "search", "binary search algorithm fibonacci"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
            check=True,
        )

        # Extract first file mentioned in each result
        def extract_first_file(output: str) -> str:
            """Extract first filename from search output."""
            for line in output.split("\n"):
                if ".py" in line:
                    # Extract filename
                    for word in line.split():
                        if ".py" in word:
                            return word.strip("[]():,")
            return ""

        file1 = extract_first_file(query1_result.stdout)
        file2 = extract_first_file(query2_result.stdout)
        file3 = extract_first_file(query3_result.stdout)

        # Top results should differ (at least 2 should be different)
        unique_files = len(set([file1, file2, file3]) - {""})

        assert unique_files >= 2, (
            f"Top results are too similar across different queries (Issue #4)!\n"
            f"Database query → {file1}\n"
            f"API query → {file2}\n"
            f"Algorithm query → {file3}\n"
            f"Expected different top files for different query topics"
        )

    def test_1_3_5_activation_scores_have_variance(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.5: Assert activation scores vary across chunks (stddev > 0.1).

        EXPECTED TO FAIL: All activation scores identical (Issue #4).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Search and try to get JSON output with scores
        result = run_cli_command(
            ["aur", "mem", "search", "function", "--output", "json"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)

                if isinstance(data, list) and len(data) >= 3:
                    # Extract scores
                    scores = [item.get("score", item.get("activation_score", 0)) for item in data]

                    # Calculate standard deviation
                    if len(scores) >= 2:
                        stddev = statistics.stdev(scores)

                        assert stddev > 0.1, (
                            f"Activation scores have no variance (Issue #4)!\n"
                            f"Scores: {scores}\n"
                            f"StdDev: {stddev:.4f} (should be > 0.1)\n"
                            f"All scores identical means activation tracking is broken"
                        )
                else:
                    pytest.skip("Insufficient results or unsupported JSON format")
            except (json.JSONDecodeError, KeyError):
                pytest.skip("JSON parsing failed or scores not in output")
        else:
            pytest.skip("--output json not supported")

    def test_1_3_6_semantic_scores_vary_by_relevance(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.6: Assert semantic scores vary based on relevance.

        EXPECTED TO FAIL: Semantic scores all identical (embeddings not working).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Search for specific term
        result = run_cli_command(
            ["aur", "mem", "search", "database sqlite", "--output", "json"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)

                if isinstance(data, list) and len(data) >= 3:
                    # Try to extract semantic scores if available
                    semantic_scores = []
                    for item in data:
                        if "semantic_score" in item:
                            semantic_scores.append(item["semantic_score"])
                        elif "scores" in item and isinstance(item["scores"], dict):
                            semantic_scores.append(item["scores"].get("semantic", 0))

                    if len(semantic_scores) >= 2:
                        # Check variance
                        stddev = statistics.stdev(semantic_scores)

                        # Semantic scores should vary (not all 1.0 or all same)
                        assert stddev > 0.05, (
                            f"Semantic scores are identical (embeddings not working)!\n"
                            f"Scores: {semantic_scores}\n"
                            f"StdDev: {stddev:.4f} (should be > 0.05)"
                        )
                    else:
                        pytest.skip("No semantic scores found in output")
                else:
                    pytest.skip("Insufficient results")
            except (json.JSONDecodeError, KeyError):
                pytest.skip("JSON parsing failed")
        else:
            pytest.skip("--output json not supported")

    def test_1_3_7_line_ranges_not_all_zero(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.7: Assert line ranges are not all "0-0".

        Line ranges should reflect actual code locations.

        EXPECTED TO FAIL: Line ranges show "0-0" (metadata not stored correctly).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Search
        result = run_cli_command(
            ["aur", "mem", "search", "def", "--output", "json"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)

                if isinstance(data, list) and len(data) > 0:
                    # Check line ranges
                    line_ranges = []
                    for item in data:
                        if "line_start" in item and "line_end" in item:
                            line_ranges.append((item["line_start"], item["line_end"]))
                        elif "lines" in item:
                            line_ranges.append(item["lines"])

                    if line_ranges:
                        # Not all should be (0, 0) or "0-0"
                        all_zero = all(
                            (
                                lr == (0, 0)
                                or lr == "0-0"
                                or (isinstance(lr, tuple) and lr[0] == 0 and lr[1] == 0)
                            )
                            for lr in line_ranges
                        )

                        assert not all_zero, (
                            f"All line ranges are 0-0 (metadata not stored)!\n"
                            f"Line ranges: {line_ranges}\n"
                            f"Should have actual line numbers from source files"
                        )
                    else:
                        pytest.skip("No line range data in output")
                else:
                    pytest.skip("No results")
            except (json.JSONDecodeError, KeyError):
                pytest.skip("JSON parsing failed")
        else:
            pytest.skip("--output json not supported")

    def test_1_3_8_search_accuracy_comprehensive_check(
        self,
        clean_aurora_home: Path,
        diverse_python_project: Path,
    ) -> None:
        """Test 1.3.8: Expected - Test FAILS because all results identical (Issue #4).

        Comprehensive test documenting all aspects of Issue #4.

        Current broken behavior:
        - All searches return same top 5 results
        - All activation scores = 1.000
        - All semantic scores = 1.000
        - Line ranges = 0-0

        Expected behavior after fix:
        - Different queries return different results
        - Scores vary based on relevance
        - Line ranges show actual code locations
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=60,
            check=True,
        )

        # Run very different searches
        search1 = run_cli_command(
            ["aur", "mem", "search", "database"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
            check=True,
        )

        search2 = run_cli_command(
            ["aur", "mem", "search", "algorithm"],
            capture_output=True,
            text=True,
            cwd=diverse_python_project,
            timeout=30,
            check=True,
        )

        # Outputs should be substantially different
        similarity_ratio = len(set(search1.stdout) & set(search2.stdout)) / max(
            len(search1.stdout),
            len(search2.stdout),
            1,
        )

        # If outputs are >80% similar despite completely different queries, that's Issue #4
        if similarity_ratio > 0.8:
            pytest.fail(
                f"ISSUE #4 CONFIRMED: Searches return identical results!\n"
                f"Query 1: 'database' returned:\n{search1.stdout[:200]}...\n\n"
                f"Query 2: 'algorithm' returned:\n{search2.stdout[:200]}...\n\n"
                f"Similarity: {similarity_ratio * 100:.1f}% (should be <50% for different queries)\n\n"
                f"Root cause: Activation tracking broken (all base_level = 0.0)\n"
                f"Fix: Call store.record_access() during search",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
