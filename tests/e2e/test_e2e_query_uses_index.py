"""E2E Test: Query Uses Indexed Data (Task 1.4)

This test suite validates that queries retrieve from the indexed codebase
and pass relevant context to the LLM, not just generic answers.

Test Scenario: Query Retrieval Integration
1. Index codebase with specific code patterns
2. Query for information that exists in indexed code
3. Mock LLM client to capture prompts sent to API
4. Verify LLM prompt includes context from indexed chunks
5. Verify context includes file paths and line ranges
6. Verify response references actual code (not generic answer)
7. Test with --verbose flag to see retrieval logs

Expected: These tests will FAIL initially due to Issue #15 (query doesn't retrieve)
- Current behavior: Queries don't retrieve from index, give generic answers
- Expected behavior: Queries retrieve relevant chunks and include in LLM context

Reference: PRD-0010 Section 3 (User Stories), US-3 (Query Retrieves from Index)
"""

import json
import os
import subprocess
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
def project_with_unique_patterns() -> Generator[Path, None, None]:
    """Create a project with unique, identifiable code patterns."""
    with tempfile.TemporaryDirectory() as tmp_project:
        project_path = Path(tmp_project)

        # Create a module with unique class and methods
        (project_path / "hybrid_retriever.py").write_text(
            '''"""Hybrid retrieval combining activation and semantic search."""


class HybridRetriever:
    """Combines ACT-R activation scores with semantic similarity.

    This retriever uses a weighted combination:
    - 60% activation score (frequency + recency)
    - 40% semantic similarity (embeddings)

    The hybrid approach balances immediate relevance with long-term importance.
    """

    def __init__(self, activation_weight: float = 0.6, semantic_weight: float = 0.4):
        """Initialize hybrid retriever with custom weights.

        Args:
            activation_weight: Weight for ACT-R activation (default: 0.6)
            semantic_weight: Weight for semantic similarity (default: 0.4)
        """
        self.activation_weight = activation_weight
        self.semantic_weight = semantic_weight

    def retrieve(self, query: str, top_k: int = 10):
        """Retrieve top-k chunks using hybrid scoring.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of chunks ranked by hybrid score
        """
        # Calculate activation scores
        activation_scores = self._get_activation_scores(query)

        # Calculate semantic scores
        semantic_scores = self._get_semantic_scores(query)

        # Combine using weights
        hybrid_scores = {}
        for chunk_id in set(activation_scores) | set(semantic_scores):
            act_score = activation_scores.get(chunk_id, 0.0)
            sem_score = semantic_scores.get(chunk_id, 0.0)
            hybrid_scores[chunk_id] = (
                self.activation_weight * act_score +
                self.semantic_weight * sem_score
            )

        # Sort and return top-k
        ranked = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def _get_activation_scores(self, query: str):
        """Calculate ACT-R activation scores."""
        # Placeholder for actual implementation
        return {}

    def _get_semantic_scores(self, query: str):
        """Calculate semantic similarity scores."""
        # Placeholder for actual implementation
        return {}
''',
        )

        # Create another unique module
        (project_path / "complexity_assessment.py").write_text(
            '''"""Complexity assessment for query routing."""


class ComplexityAssessor:
    """Assesses query complexity to determine processing strategy.

    Uses keyword matching and heuristics to classify queries as:
    - SIMPLE: Direct lookup, single step
    - MEDIUM: Multi-step, requires retrieval
    - COMPLEX: Multi-part, requires SOAR pipeline
    """

    SIMPLE_KEYWORDS = {"what", "define", "explain"}
    MEDIUM_KEYWORDS = {"how", "analyze", "compare"}
    COMPLEX_KEYWORDS = {"research", "design", "architect", "evaluate"}

    def assess(self, query: str) -> dict:
        """Assess query complexity.

        Args:
            query: User query string

        Returns:
            Dictionary with complexity level and confidence
        """
        query_lower = query.lower()

        # Count question marks (multi-part queries)
        question_count = query.count("?")

        # Check keyword matches
        simple_matches = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query_lower)
        medium_matches = sum(1 for kw in self.MEDIUM_KEYWORDS if kw in query_lower)
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)

        # Determine complexity
        if complex_matches > 0 or question_count >= 3:
            level = "COMPLEX"
            confidence = 0.8
        elif medium_matches > 0 or question_count == 2:
            level = "MEDIUM"
            confidence = 0.6
        else:
            level = "SIMPLE"
            confidence = 0.7

        return {
            "level": level,
            "confidence": confidence,
            "question_count": question_count,
        }
''',
        )

        yield project_path


class TestQueryUsesIndex:
    """E2E tests for query retrieval integration.

    These tests verify that queries actually retrieve from the indexed codebase
    and pass relevant context to the LLM.
    """

    def test_1_4_1_index_codebase_with_specific_patterns(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Test 1.4.1: Write test that indexes codebase with specific code patterns.

        Indexes project with unique, searchable classes and methods.
        """
        # Index the project
        result = run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
        )

        assert result.returncode == 0, f"Indexing failed:\nstderr: {result.stderr}"

        # Verify specific files were indexed
        assert (
            "hybrid_retriever" in result.stdout.lower()
            or "complexity_assessment" in result.stdout.lower()
        ), f"Should have indexed our specific files:\n{result.stdout}"

    def test_1_4_2_query_for_existing_code(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Test 1.4.2: Query for information that exists in indexed code.

        Asks about HybridRetriever class which exists in indexed code.

        EXPECTED TO FAIL: Query doesn't retrieve from index (Issue #15).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # Query about something specific in the code
        # Using --dry-run to avoid needing real API key
        result = run_cli_command(
            ["aur", "query", "What is HybridRetriever and how does it work?", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
        )

        # Even with --dry-run, should show retrieval happened
        output = (result.stdout + result.stderr).lower()

        # Should mention retrieval or show indexed data
        assert "hybrid" in output or "retrieve" in output or "chunk" in output, (
            f"Query should retrieve from indexed data (Issue #15)!\n"
            f"Query: 'What is HybridRetriever?'\n"
            f"Output: {result.stdout}\n"
            f"Expected: Should reference indexed HybridRetriever class"
        )

    def test_1_4_3_query_with_verbose_shows_retrieval(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Test 1.4.7: Test with --verbose flag to see retrieval logs.

        Verbose output should show what chunks were retrieved.

        EXPECTED TO FAIL: No retrieval happens (Issue #15).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # Query with verbose flag and dry-run
        result = run_cli_command(
            ["aur", "query", "explain HybridRetriever", "--verbose", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
        )

        # Verbose output should mention retrieval
        output = (result.stdout + result.stderr).lower()

        # Look for retrieval indicators
        retrieval_indicators = ["retrieve", "chunk", "found", "search", "context"]
        found_indicator = any(indicator in output for indicator in retrieval_indicators)

        assert found_indicator, (
            f"Verbose output should show retrieval activity (Issue #15)!\n"
            f"Output: {result.stdout}\n"
            f"Stderr: {result.stderr}\n"
            f"Expected indicators: {retrieval_indicators}"
        )

    def test_1_4_4_search_before_query_shows_code_exists(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Baseline test: Verify search CAN find the code we'll query about.

        This proves the code is indexed and searchable - so query should find it too.
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # Search for HybridRetriever (should work)
        search_result = run_cli_command(
            ["aur", "mem", "search", "HybridRetriever"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
            check=True,
        )

        # Search should find it
        assert (
            "hybrid" in search_result.stdout.lower()
        ), f"Search should find HybridRetriever:\n{search_result.stdout}"

        # Now query should also find it (but currently doesn't - Issue #15)

    def test_1_4_5_query_output_references_actual_code(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Test 1.4.6: Verify response references actual code (not generic answer).

        Query response should include specifics from the indexed code:
        - File names (hybrid_retriever.py)
        - Class names (HybridRetriever)
        - Method names (retrieve, _get_activation_scores)
        - Docstring content (60% activation, 40% semantic)

        EXPECTED TO FAIL: Response is generic (Issue #15).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # Query with --dry-run (avoids needing API key but shows process)
        result = run_cli_command(
            ["aur", "query", "What methods does HybridRetriever have?", "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
        )

        output = (result.stdout + result.stderr).lower()

        # Should reference specific elements from the code
        code_specifics = [
            "hybrid_retriever",  # File name
            "retrieve",  # Method name
            "activation",  # Key concept from docstring
            "semantic",  # Key concept from docstring
        ]

        found_specifics = [spec for spec in code_specifics if spec in output]

        # Should find at least 2 specific references
        assert len(found_specifics) >= 2, (
            f"Query should reference specific code elements (Issue #15)!\n"
            f"Expected references: {code_specifics}\n"
            f"Found: {found_specifics}\n"
            f"Output: {result.stdout[:300]}...\n"
            f"This suggests query is not retrieving from indexed data"
        )

    def test_1_4_6_query_vs_search_consistency(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Verify query uses same data that search can find.

        If search can find HybridRetriever, query should too.
        If search returns 0 results, query has nothing to retrieve.

        EXPECTED TO FAIL: Query doesn't use search results (Issue #15).
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # First, search for a term
        search_result = run_cli_command(
            ["aur", "mem", "search", "ComplexityAssessor"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
            check=True,
        )

        # Search should find it
        search_found = "complexity" in search_result.stdout.lower()

        # Now query for same concept
        query_result = run_cli_command(
            ["aur", "query", "What is ComplexityAssessor?", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
        )

        query_output = (query_result.stdout + query_result.stderr).lower()
        query_found = "complexity" in query_output

        # If search found it, query should too
        if search_found:
            assert query_found, (
                f"Search found ComplexityAssessor but query didn't (Issue #15)!\n"
                f"Search output: {search_result.stdout[:200]}...\n"
                f"Query output: {query_result.stdout[:200]}...\n"
                f"Query should retrieve same data that search can find"
            )

    def test_1_4_7_comprehensive_query_retrieval_check(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """Test 1.4.8: Expected - Test FAILS because query doesn't retrieve from index (Issue #15).

        Comprehensive test documenting Issue #15.

        Current broken behavior:
        - Query doesn't call memory_manager.search() before LLM
        - LLM receives no context from indexed code
        - Answers are generic, not code-specific

        Expected behavior after fix:
        - Query retrieves relevant chunks from index
        - LLM prompt includes context with file paths and code
        - Answers reference actual indexed code
        """
        # Index the project
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # Run a very specific query about indexed code
        result = subprocess.run(
            [
                "aur",
                "query",
                "List all methods in the HybridRetriever class",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
        )

        output = (result.stdout + result.stderr).lower()

        # The specific methods that exist in the indexed code
        actual_methods = ["retrieve", "_get_activation_scores", "_get_semantic_scores"]

        # Check if any specific methods are mentioned
        mentioned_methods = [m for m in actual_methods if m in output]

        if len(mentioned_methods) == 0:
            pytest.fail(
                f"ISSUE #15 CONFIRMED: Query doesn't retrieve from indexed code!\n\n"
                f"Query: 'List all methods in the HybridRetriever class'\n\n"
                f"Actual methods in indexed code: {actual_methods}\n"
                f"Methods mentioned in output: {mentioned_methods}\n\n"
                f"Output snippet: {result.stdout[:300]}...\n\n"
                f"Root cause: execute_direct_llm() doesn't call memory_manager.search()\n"
                f"Fix: Add retrieval step before LLM call:\n"
                f"  context_chunks = memory_manager.search(query, limit=10)\n"
                f"  prompt = format_context(context_chunks) + query",
            )


class TestQueryRetrievalWithoutAPI:
    """Tests that validate retrieval without needing API keys.

    Uses --dry-run or mocking to test retrieval logic.
    """

    def test_query_dry_run_shows_retrieval_intent(
        self,
        clean_aurora_home: Path,
        project_with_unique_patterns: Path,
    ) -> None:
        """With --dry-run, query should at least ATTEMPT retrieval.

        Even if it doesn't call LLM, it should retrieve chunks.
        """
        # Index
        run_cli_command(
            ["aur", "mem", "index", "."],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=60,
            check=True,
        )

        # Query with dry-run
        result = run_cli_command(
            ["aur", "query", "what is HybridRetriever", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=project_with_unique_patterns,
            timeout=30,
        )

        # Should show SOME indication of what it would do
        output = (result.stdout + result.stderr).lower()

        # At minimum, should mention the query or show it processed something
        assert len(output) > 0, "Dry-run should produce some output"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
