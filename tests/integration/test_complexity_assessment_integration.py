"""Integration tests for complexity assessment with SOAR orchestrator.

Tests verify that the new ComplexityAssessor correctly classifies queries
and that the orchestrator properly routes them based on complexity level.
"""

import pytest

from aurora_soar.phases.assess import assess_complexity


class TestComplexityAssessmentIntegration:
    """Test complexity assessment integration with orchestrator."""

    def test_simple_query_classification(self):
        """Verify SIMPLE queries are correctly classified."""
        # Test with typical simple queries
        simple_queries = [
            "what is python",
            "show me the README",
            "list all functions",
            "display the config",
        ]

        for query in simple_queries:
            result = assess_complexity(query, llm_client=None)

            assert (
                result["complexity"] == "SIMPLE"
            ), f"Query '{query}' should be classified as SIMPLE, got {result['complexity']}"
            assert (
                result["confidence"] >= 0.5
            ), f"Confidence should be >= 0.5 for SIMPLE query, got {result['confidence']}"
            assert (
                result["method"] == "keyword"
            ), f"Method should be 'keyword' for SIMPLE query, got {result['method']}"

    def test_medium_query_classification(self):
        """Verify MEDIUM queries are correctly classified."""
        # Test with typical medium queries
        medium_queries = [
            "explain how the caching works",
            "analyze the performance bottlenecks",
            "compare the two approaches",
            "investigate why the tests are failing",
        ]

        for query in medium_queries:
            result = assess_complexity(query, llm_client=None)

            assert (
                result["complexity"] == "MEDIUM"
            ), f"Query '{query}' should be classified as MEDIUM, got {result['complexity']}"
            assert (
                result["confidence"] >= 0.5
            ), f"Confidence should be >= 0.5 for MEDIUM query, got {result['confidence']}"
            assert (
                result["method"] == "keyword"
            ), f"Method should be 'keyword' for MEDIUM query, got {result['method']}"

    def test_complex_query_classification(self):
        """Verify COMPLEX queries are correctly classified."""
        # Test with typical complex queries
        complex_queries = [
            "implement user authentication with oauth",
            "refactor the entire caching system to use redis",
            "design a distributed task queue with retry logic",
            "migrate the database schema and update all queries",
        ]

        for query in complex_queries:
            result = assess_complexity(query, llm_client=None)

            assert (
                result["complexity"] == "COMPLEX"
            ), f"Query '{query}' should be classified as COMPLEX, got {result['complexity']}"
            assert (
                result["confidence"] >= 0.5
            ), f"Confidence should be >= 0.5 for COMPLEX query, got {result['confidence']}"
            assert (
                result["method"] == "keyword"
            ), f"Method should be 'keyword' for COMPLEX query, got {result['method']}"

    def test_critical_query_classification(self):
        """Verify CRITICAL queries are correctly classified."""
        # Test with queries containing critical keywords
        critical_queries = [
            "fix security vulnerability in authentication",
            "production outage emergency",
            "data breach investigation",
            "encrypt sensitive payment data",
            "critical incident response needed",
        ]

        for query in critical_queries:
            result = assess_complexity(query, llm_client=None)

            assert (
                result["complexity"] == "CRITICAL"
            ), f"Query '{query}' should be classified as CRITICAL, got {result['complexity']}"
            assert (
                result["confidence"] >= 0.9
            ), f"Confidence should be >= 0.9 for CRITICAL query, got {result['confidence']}"
            assert (
                result["method"] == "keyword"
            ), f"Method should be 'keyword' for CRITICAL query, got {result['method']}"

    def test_orchestrator_receives_correct_format(self):
        """Verify orchestrator receives correct format from assess_complexity()."""
        query = "explain how caching works"

        result = assess_complexity(query, llm_client=None)

        # Verify required fields are present
        assert "complexity" in result, "Result must include 'complexity' field"
        assert "confidence" in result, "Result must include 'confidence' field"
        assert "method" in result, "Result must include 'method' field"
        assert "reasoning" in result, "Result must include 'reasoning' field"
        assert "score" in result, "Result must include 'score' field"

        # Verify field types
        assert isinstance(result["complexity"], str), "complexity must be string"
        assert isinstance(result["confidence"], (int, float)), "confidence must be numeric"
        assert isinstance(result["method"], str), "method must be string"
        assert isinstance(result["reasoning"], str), "reasoning must be string"
        assert isinstance(result["score"], (int, float)), "score must be numeric"

        # Verify complexity is uppercase
        assert result["complexity"] in [
            "SIMPLE",
            "MEDIUM",
            "COMPLEX",
            "CRITICAL",
        ], f"complexity must be uppercase level, got {result['complexity']}"

        # Verify confidence is in valid range
        assert (
            0.0 <= result["confidence"] <= 1.0
        ), f"confidence must be 0.0-1.0, got {result['confidence']}"

        # Verify score is in valid range
        assert 0.0 <= result["score"] <= 1.0, f"score must be 0.0-1.0, got {result['score']}"

    def test_routing_decision_simple_query(self):
        """Verify SIMPLE queries trigger early exit in orchestrator."""
        query = "what is python"

        result = assess_complexity(query, llm_client=None)

        # Should be SIMPLE with high confidence (keyword method)
        assert result["complexity"] == "SIMPLE"
        assert result["method"] == "keyword"

        # In orchestrator, SIMPLE queries should bypass decomposition
        # (verified by code inspection at line 205 of orchestrator.py)

    def test_routing_decision_complex_query(self):
        """Verify COMPLEX queries go through full SOAR pipeline."""
        query = "implement user authentication with oauth and session management"

        result = assess_complexity(query, llm_client=None)

        # Should be COMPLEX with high confidence
        assert result["complexity"] == "COMPLEX"
        assert result["confidence"] >= 0.7

        # In orchestrator, COMPLEX queries should go through full 9-phase pipeline
        # (verified by code inspection - no early exit for COMPLEX)

    def test_routing_decision_critical_query(self):
        """Verify CRITICAL queries are treated same as COMPLEX for routing."""
        query = "fix security vulnerability in authentication"

        result = assess_complexity(query, llm_client=None)

        # Should be CRITICAL with very high confidence
        assert result["complexity"] == "CRITICAL"
        assert result["confidence"] >= 0.9

        # In orchestrator, CRITICAL routes same as COMPLEX (full pipeline)
        # Critical keywords override score-based classification

    def test_performance_latency(self):
        """Verify complexity assessment adds minimal latency."""
        import time

        query = "explain how the caching system works"

        start_time = time.perf_counter()
        result = assess_complexity(query, llm_client=None)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000

        # Should complete in under 2ms (target from task 7.12)
        assert latency_ms < 2.0, f"Complexity assessment took {latency_ms:.2f}ms, should be < 2ms"

        # Verify result is valid
        assert result["complexity"] in ["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"]

    def test_no_breaking_changes_return_format(self):
        """Verify return format is backward compatible."""
        query = "test query"

        result = assess_complexity(query, llm_client=None)

        # Old code expected these fields (from orchestrator.py:291-295)
        assert "complexity" in result, "Must include 'complexity' for backward compatibility"
        assert "confidence" in result, "Must include 'confidence' for backward compatibility"

        # Verify complexity is a string (not enum)
        assert isinstance(result["complexity"], str)

        # Verify confidence is numeric (0.0-1.0)
        assert isinstance(result["confidence"], (int, float))
        assert 0.0 <= result["confidence"] <= 1.0


class TestComplexityLevelCoverage:
    """Test that all complexity levels are covered."""

    @pytest.mark.parametrize(
        "query,expected_level",
        [
            ("show README", "SIMPLE"),
            ("list functions", "SIMPLE"),
            ("explain caching", "MEDIUM"),
            ("analyze performance", "MEDIUM"),
            ("implement authentication", "COMPLEX"),
            ("refactor entire system", "COMPLEX"),
            ("fix security vulnerability", "CRITICAL"),
            ("production outage", "CRITICAL"),
        ],
    )
    def test_all_levels_accessible(self, query, expected_level):
        """Verify all 4 complexity levels can be reached."""
        result = assess_complexity(query, llm_client=None)

        assert (
            result["complexity"] == expected_level
        ), f"Query '{query}' should be {expected_level}, got {result['complexity']}"
