"""E2E Test: Complexity Assessment (Task 1.5)

This test suite validates that Aurora correctly assesses query complexity
and triggers SOAR pipeline for complex queries.

Test Scenario: Complexity Assessment
1. Test multi-part query: "research X? who are Y? what features Z?"
2. Run `aur query --dry-run` to see complexity assessment
3. Parse output to extract complexity level and confidence score
4. Assert complexity is MEDIUM or COMPLEX (not SIMPLE)
5. Assert confidence score >= 0.4
6. Test domain-specific queries (SOAR, ACT-R, agentic AI)
7. Verify domain queries classified as MEDIUM/COMPLEX
8. Test simple query remains SIMPLE ("what is Python?")

Expected: These tests will FAIL initially due to Issue #6 (complexity assessment broken)
- Current behavior: All queries classified as SIMPLE
- Expected behavior: Domain queries and multi-part queries classified as MEDIUM/COMPLEX

Reference: PRD-0010 Section 3 (User Stories), US-4 (Accurate Complexity Assessment)
"""

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Dict, Optional

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


def parse_complexity_output(output: str) -> dict[str, any]:
    """Parse complexity assessment from command output.

    Args:
        output: stdout + stderr from query command

    Returns:
        Dictionary with complexity, score, confidence, decision
    """
    result = {
        "complexity": None,
        "score": None,
        "confidence": None,
        "decision": None,
    }

    output_lower = output.lower()

    # Extract complexity level
    if "complexity: complex" in output_lower:
        result["complexity"] = "COMPLEX"
    elif "complexity: medium" in output_lower:
        result["complexity"] = "MEDIUM"
    elif "complexity: simple" in output_lower:
        result["complexity"] = "SIMPLE"

    # Extract score (various formats)
    score_match = re.search(r"score[:\s]+(\d+\.\d+)", output_lower)
    if score_match:
        result["score"] = float(score_match.group(1))

    # Extract confidence
    confidence_match = re.search(r"confidence[:\s]+(\d+\.\d+)", output_lower)
    if confidence_match:
        result["confidence"] = float(confidence_match.group(1))

    # Extract decision
    if "soar" in output_lower and ("use" in output_lower or "would use" in output_lower):
        result["decision"] = "SOAR"
    elif "direct llm" in output_lower or "fast mode" in output_lower:
        result["decision"] = "DIRECT_LLM"

    return result


class TestComplexityAssessment:
    """E2E tests for query complexity assessment.

    These tests verify that Aurora correctly identifies complex queries
    and routes them to the appropriate processing pipeline.
    """

    def test_1_5_1_multi_part_query_classified_as_complex(self, clean_aurora_home: Path) -> None:
        """Test 1.5.1: Write test for multi-part query.

        Query: "research X? who are Y? what features Z?"

        EXPECTED TO FAIL: Classified as SIMPLE instead of COMPLEX (Issue #6).
        """
        # Multi-part query with 3+ questions
        query = (
            "research agentic ai market? "
            "who are the top players? "
            "what features does everyone have? "
            "when should i choose agentic ai with code vs persona md files?"
        )

        # Run with --dry-run to see assessment without API call
        result = run_cli_command(
            ["aur", "query", query, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        assessment = parse_complexity_output(output)

        # Multi-part query (4 questions) should be MEDIUM or COMPLEX
        assert assessment["complexity"] in ["MEDIUM", "COMPLEX"], (
            f"Multi-part query should be MEDIUM/COMPLEX (Issue #6)!\n"
            f"Query: {query}\n"
            f"Assessed as: {assessment['complexity']}\n"
            f"Score: {assessment.get('score', 'N/A')}\n"
            f"Confidence: {assessment.get('confidence', 'N/A')}\n"
            f"Output: {output[:300]}...\n"
            f"Expected: Query with 4 questions should trigger MEDIUM or COMPLEX"
        )

    def test_1_5_2_dry_run_shows_complexity_assessment(self, clean_aurora_home: Path) -> None:
        """Test 1.5.2: Run `aur query --dry-run` to see complexity assessment.

        Verifies --dry-run shows assessment details.
        """
        query = "explain SOAR reasoning phases in Aurora"

        result = run_cli_command(
            ["aur", "query", query, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = (result.stdout + result.stderr).lower()

        # Should show some assessment information
        assessment_indicators = ["complexity", "score", "confidence", "assess"]

        found = [ind for ind in assessment_indicators if ind in output]

        assert len(found) > 0, (
            f"--dry-run should show complexity assessment!\n"
            f"Expected indicators: {assessment_indicators}\n"
            f"Found: {found}\n"
            f"Output: {result.stdout}"
        )

    def test_1_5_3_parse_complexity_level_and_confidence(self, clean_aurora_home: Path) -> None:
        """Test 1.5.3: Parse output to extract complexity level and confidence score.

        Verifies we can extract assessment details from output.
        """
        query = "research machine learning frameworks and compare features"

        result = run_cli_command(
            ["aur", "query", query, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        assessment = parse_complexity_output(output)

        # Should have extracted at least complexity level
        assert assessment["complexity"] is not None, (
            f"Should be able to parse complexity level from output!\n"
            f"Output: {output[:300]}...\n"
            f"Parsed: {assessment}"
        )

    def test_1_5_4_complexity_not_always_simple(self, clean_aurora_home: Path) -> None:
        """Test 1.5.4: Assert complexity is MEDIUM or COMPLEX (not SIMPLE).

        For queries that are clearly complex.

        EXPECTED TO FAIL: All queries assessed as SIMPLE (Issue #6).
        """
        # Various complex queries
        complex_queries = [
            "research and compare agentic AI frameworks",
            "analyze the architecture of SOAR and ACT-R systems",
            "design a cognitive reasoning pipeline with multiple phases",
            "what are the differences between activation spreading and semantic search?",
        ]

        results = []
        for query in complex_queries:
            result = run_cli_command(
                ["aur", "query", query, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            assessment = parse_complexity_output(output)
            results.append((query, assessment))

        # At least 2 of these should be MEDIUM or COMPLEX
        non_simple = [r for r in results if r[1]["complexity"] in ["MEDIUM", "COMPLEX"]]

        assert len(non_simple) >= 2, (
            "Complex queries should not all be SIMPLE (Issue #6)!\n"
            + "\n".join(f"  - {q[:50]}... → {a['complexity']}" for q, a in results)
            + f"\n\nAt least 2 should be MEDIUM/COMPLEX, got {len(non_simple)}"
        )

    def test_1_5_5_confidence_score_reasonable(self, clean_aurora_home: Path) -> None:
        """Test 1.5.5: Assert confidence score >= 0.4.

        For queries with clear complexity indicators.
        """
        query = "research SOAR cognitive architecture and compare with ACT-R"

        result = run_cli_command(
            ["aur", "query", query, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        assessment = parse_complexity_output(output)

        # Confidence should be reasonable (>= 0.4) when domain keywords match
        if assessment["confidence"] is not None:
            assert assessment["confidence"] >= 0.4, (
                f"Confidence should be >= 0.4 for query with clear indicators!\n"
                f"Query: {query}\n"
                f"Confidence: {assessment['confidence']}\n"
                f"Complexity: {assessment['complexity']}\n"
                f"Keywords matched: SOAR, cognitive, architecture, ACT-R, research, compare"
            )
        else:
            pytest.skip("Could not parse confidence from output")

    def test_1_5_6_domain_specific_queries_soar(self, clean_aurora_home: Path) -> None:
        """Test 1.5.6: Test domain-specific queries (SOAR, ACT-R, agentic AI).

        EXPECTED TO FAIL: Domain terms not in keyword list (Issue #6).
        """
        domain_queries = [
            "explain SOAR reasoning phases",
            "how does ACT-R activation spreading work?",
            "what is agentic AI and how does it differ from traditional AI?",
            "describe the Aurora cognitive architecture",
        ]

        results = []
        for query in domain_queries:
            result = run_cli_command(
                ["aur", "query", query, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            assessment = parse_complexity_output(output)
            results.append((query, assessment))

        # Domain queries should be at least MEDIUM
        non_simple = [r for r in results if r[1]["complexity"] in ["MEDIUM", "COMPLEX"]]

        assert len(non_simple) >= 2, (
            "Domain-specific queries should be MEDIUM/COMPLEX (Issue #6)!\n"
            + "\n".join(f"  - {q[:50]}... → {a['complexity']}" for q, a in results)
            + "\n\nDomain terms (SOAR, ACT-R, agentic, Aurora) should trigger MEDIUM"
        )

    def test_1_5_7_domain_queries_classified_correctly(self, clean_aurora_home: Path) -> None:
        """Test 1.5.7: Verify domain queries classified as MEDIUM/COMPLEX.

        Specifically tests Aurora-related terminology.

        EXPECTED TO FAIL: Domain keywords missing from assess.py (Issue #6).
        """
        query = "how does Aurora's hybrid retrieval combine activation and semantic scoring?"

        result = run_cli_command(
            ["aur", "query", query, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr
        assessment = parse_complexity_output(output)

        # Query has domain terms: Aurora, hybrid, retrieval, activation, semantic
        # Should be MEDIUM at minimum
        assert assessment["complexity"] in ["MEDIUM", "COMPLEX"], (
            f"Domain query should be MEDIUM/COMPLEX (Issue #6)!\n"
            f"Query: {query}\n"
            f"Assessed as: {assessment['complexity']}\n"
            f"Domain terms present: Aurora, hybrid, retrieval, activation, semantic\n"
            f"Expected: MEDIUM (requires Aurora knowledge)"
        )

    def test_1_5_8_simple_query_remains_simple(self, clean_aurora_home: Path) -> None:
        """Test 1.5.8: Test simple query remains SIMPLE ("what is Python?").

        Verifies assessment doesn't over-classify simple queries.
        """
        simple_queries = [
            "what is Python?",
            "define variable",
            "explain function",
        ]

        results = []
        for query in simple_queries:
            result = run_cli_command(
                ["aur", "query", query, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            assessment = parse_complexity_output(output)
            results.append((query, assessment))

        # At least 2 should be SIMPLE
        simple_count = len([r for r in results if r[1]["complexity"] == "SIMPLE"])

        assert simple_count >= 2, (
            "Simple queries should be classified as SIMPLE!\n"
            + "\n".join(f"  - {q} → {a['complexity']}" for q, a in results)
            + f"\n\nAt least 2 should be SIMPLE, got {simple_count}"
        )

    def test_1_5_9_comprehensive_complexity_assessment_check(self, clean_aurora_home: Path) -> None:
        """Test 1.5.9: Expected - Test FAILS because complexity always SIMPLE (Issue #6).

        Comprehensive test documenting Issue #6.

        Current broken behavior:
        - All queries classified as SIMPLE
        - Domain keywords not in assessment (SOAR, ACT-R, agentic, Aurora)
        - Multi-question detection missing (doesn't count ?)
        - Confidence scores too low

        Expected behavior after fix:
        - Domain queries → MEDIUM
        - Multi-part queries (2+ ?) → COMPLEX
        - Research/analyze/compare → MEDIUM
        - Simple lookups → SIMPLE
        """
        test_cases = [
            # (query, expected_min_complexity, reason)
            (
                "research agentic AI market? who are top players? what features?",
                "MEDIUM",
                "Multi-part (3 questions) + research keyword",
            ),
            ("explain SOAR reasoning phases", "MEDIUM", "Domain keyword: SOAR"),
            ("how does ACT-R activation work?", "MEDIUM", "Domain keyword: ACT-R"),
            ("what is Python?", "SIMPLE", "Simple definition query"),
            (
                "analyze and compare Aurora with traditional systems",
                "MEDIUM",
                "Analyze + compare keywords + domain (Aurora)",
            ),
        ]

        failures = []
        for query, expected_min, reason in test_cases:
            result = run_cli_command(
                ["aur", "query", query, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            assessment = parse_complexity_output(output)
            actual = assessment["complexity"]

            # Check if assessment meets minimum expectation
            complexity_order = {"SIMPLE": 0, "MEDIUM": 1, "COMPLEX": 2}
            expected_level = complexity_order.get(expected_min, 0)
            actual_level = complexity_order.get(actual, 0)

            if actual_level < expected_level:
                failures.append(
                    f"  ❌ '{query[:60]}...'\n"
                    f"     Expected: >= {expected_min}, Got: {actual}\n"
                    f"     Reason: {reason}"
                )

        if failures:
            pytest.fail(
                f"ISSUE #6 CONFIRMED: Complexity assessment broken!\n\n"
                f"Failed {len(failures)}/{len(test_cases)} test cases:\n\n"
                + "\n\n".join(failures)
                + "\n\n"
                "Root causes:\n"
                "1. Missing domain keywords in assess.py:\n"
                "   - MEDIUM_KEYWORDS needs: soar, actr, activation, retrieval,\n"
                "     reasoning, agentic, marketplace, aurora\n"
                "2. No multi-question detection (should count '?')\n"
                "3. Missing scope keywords: research, analyze, compare\n\n"
                "Fix location: packages/soar/src/aurora_soar/phases/assess.py"
            )


class TestComplexityAssessmentEdgeCases:
    """Test edge cases and boundary conditions for complexity assessment."""

    def test_multiple_questions_boost_complexity(self, clean_aurora_home: Path) -> None:
        """Queries with 2+ question marks should be boosted to MEDIUM/COMPLEX.

        EXPECTED TO FAIL: Multi-question detection not implemented (Issue #6).
        """
        # Same base query, but with different question counts
        base = "explain SOAR reasoning"
        single_q = f"{base}?"
        double_q = f"{base}? how does it work?"
        triple_q = f"{base}? how does it work? what are the phases?"

        results = []
        for query, q_count in [(single_q, 1), (double_q, 2), (triple_q, 3)]:
            result = run_cli_command(
                ["aur", "query", query, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            assessment = parse_complexity_output(output)
            results.append((q_count, assessment["complexity"]))

        # Queries with 2+ questions should be more complex
        # At minimum, 3-question query should be COMPLEX or MEDIUM
        triple_q_complexity = results[2][1]

        assert triple_q_complexity in ["MEDIUM", "COMPLEX"], (
            f"Query with 3 questions should be MEDIUM/COMPLEX (Issue #6)!\n"
            f"Results:\n"
            f"  1 question: {results[0][1]}\n"
            f"  2 questions: {results[1][1]}\n"
            f"  3 questions: {results[2][1]}\n"
            f"Expected: Multi-question queries should be boosted"
        )

    def test_scope_keywords_trigger_medium(self, clean_aurora_home: Path) -> None:
        """Queries with scope keywords (research, analyze, compare) should be MEDIUM.

        EXPECTED TO FAIL: Scope keywords missing from assess.py (Issue #6).
        """
        scope_queries = [
            "research machine learning frameworks",
            "analyze the performance of different algorithms",
            "compare Python and JavaScript for web development",
            "design a scalable architecture for microservices",
        ]

        results = []
        for query in scope_queries:
            result = run_cli_command(
                ["aur", "query", query, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            assessment = parse_complexity_output(output)
            results.append((query, assessment["complexity"]))

        # At least 2 should be MEDIUM or COMPLEX
        non_simple = [r for r in results if r[1] in ["MEDIUM", "COMPLEX"]]

        assert len(non_simple) >= 2, (
            "Scope keywords should trigger MEDIUM (Issue #6)!\n"
            + "\n".join(f"  - {q[:50]}... → {c}" for q, c in results)
            + "\n\nKeywords: research, analyze, compare, design should trigger MEDIUM"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
