"""End-to-End Integration Tests for Simple Query Flow.

This module tests the complete SOAR pipeline for SIMPLE complexity queries,
which bypass decomposition and use a direct solving approach.

Key aspects tested:
- Phase 1: Assess complexity (keyword-based, should classify as SIMPLE)
- Phase 2: Retrieve context (with SIMPLE budget limit)
- Simple path execution (bypass decomposition phases 3-4)
- Direct solving LLM call
- Phase 9: Response formatting

Performance requirements:
- Simple query latency: <2s
"""

from __future__ import annotations

import time
from tempfile import TemporaryDirectory

import pytest

from tests.integration.test_e2e_framework import E2ETestFramework, MockLLMResponse


@pytest.fixture
def e2e_framework():
    """Create E2E test framework."""
    with TemporaryDirectory() as temp_dir:
        framework = E2ETestFramework(temp_dir)
        yield framework
        framework.cleanup()


class TestSimpleQueryE2E:
    """End-to-end tests for simple query processing."""

    def test_simple_query_bypasses_decomposition(self, e2e_framework):
        """Test that SIMPLE queries bypass decomposition phases."""
        # Configure mock LLM responses
        # Assessment should return SIMPLE complexity
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        # Simple path should call solving LLM directly (not decompose)
        solving_response = MockLLMResponse(
            content="The function calculates the sum of two numbers.",
            input_tokens=150,
            output_tokens=20,
        )
        e2e_framework.mock_llm.configure_response("sum", solving_response)

        # Create orchestrator
        orchestrator = e2e_framework.create_orchestrator()

        # Execute simple query
        query = "What does the sum function do?"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify response structure
        assert "answer" in response
        assert "confidence" in response
        assert "metadata" in response

        # Verify assessment phase executed
        e2e_framework.assert_phase_executed(response, "phase1_assess")
        assert response["metadata"]["phases"]["phase1_assess"]["complexity"] == "SIMPLE"

        # Verify retrieval phase executed
        e2e_framework.assert_phase_executed(response, "phase2_retrieve")

        # Verify decomposition phases SKIPPED
        assert (
            "phase3_decompose" not in response["metadata"]["phases"]
        ), "SIMPLE query should skip decomposition"
        assert (
            "phase4_verify" not in response["metadata"]["phases"]
        ), "SIMPLE query should skip verification"
        assert (
            "phase5_route" not in response["metadata"]["phases"]
        ), "SIMPLE query should skip routing"
        assert (
            "phase6_collect" not in response["metadata"]["phases"]
        ), "SIMPLE query should skip agent execution"

        # Verify response phase executed
        e2e_framework.assert_phase_executed(response, "phase9_respond")

    def test_simple_query_performance(self, e2e_framework):
        """Test that SIMPLE queries complete in <2s."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="This is a simple answer.",
            input_tokens=100,
            output_tokens=15,
        )
        e2e_framework.mock_llm.configure_response("query", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        # Measure execution time
        query = "What is a simple query?"
        start_time = time.time()
        response = orchestrator.execute(query, verbosity="QUIET")
        elapsed_time = time.time() - start_time

        # Verify performance requirement: <2s
        assert elapsed_time < 2.0, f"Simple query took {elapsed_time:.2f}s, expected <2s"

        # Verify response completed successfully
        assert response["confidence"] > 0
        assert "answer" in response

    def test_simple_query_budget_allocation(self, e2e_framework):
        """Test that SIMPLE queries use minimal budget allocation."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="Budget-conscious response.",
            input_tokens=100,
            output_tokens=10,
        )
        e2e_framework.mock_llm.configure_response("budget", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        # Execute query
        query = "What is the budget?"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify minimal context retrieval (SIMPLE budget: 5 chunks)
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]
        assert retrieve_meta["budget"] == 5, "SIMPLE queries should have budget of 5 chunks"

        # Verify low cost
        total_cost = response["metadata"].get("total_cost_usd", 0)
        assert total_cost < 0.01, f"SIMPLE query cost ${total_cost}, expected <$0.01"

    def test_simple_query_cost_tracking(self, e2e_framework):
        """Test that cost tracking works for simple queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="Cost-tracked response.",
            input_tokens=120,
            output_tokens=25,
        )
        e2e_framework.mock_llm.configure_response("cost", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        # Track initial budget
        initial_status = e2e_framework.cost_tracker.get_status()
        initial_consumed = initial_status["consumed_usd"]

        # Execute query
        query = "What is the cost?"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify cost was tracked
        assert "total_cost_usd" in response["metadata"]
        assert response["metadata"]["total_cost_usd"] > 0

        # Verify budget tracker updated
        final_status = e2e_framework.cost_tracker.get_status()
        final_consumed = final_status["consumed_usd"]
        assert final_consumed > initial_consumed, "Budget should be updated"

    def test_simple_query_verbosity_levels(self, e2e_framework):
        """Test that all verbosity levels work for simple queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="Verbosity test response.",
            input_tokens=100,
            output_tokens=15,
        )
        e2e_framework.mock_llm.configure_response("verbosity", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        query = "Test verbosity"

        # Test QUIET mode
        response_quiet = orchestrator.execute(query, verbosity="QUIET")
        assert "answer" in response_quiet
        # QUIET mode should have minimal metadata
        assert "metadata" in response_quiet

        # Reset mock for next call
        e2e_framework.mock_llm.configure_response("verbosity", solving_response)
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        # Test NORMAL mode
        response_normal = orchestrator.execute(query, verbosity="NORMAL")
        assert "answer" in response_normal
        assert "metadata" in response_normal
        assert "phases" in response_normal["metadata"]

        # Reset mock for next call
        e2e_framework.mock_llm.configure_response("verbosity", solving_response)
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        # Test VERBOSE mode
        response_verbose = orchestrator.execute(query, verbosity="VERBOSE")
        assert "answer" in response_verbose
        assert "metadata" in response_verbose
        assert "phases" in response_verbose["metadata"]
        assert "reasoning_trace" in response_verbose

    def test_simple_query_keyword_detection(self, e2e_framework):
        """Test that keyword-based assessment correctly identifies SIMPLE queries."""
        # For SIMPLE queries, keyword assessment should be sufficient (no LLM call)
        orchestrator = e2e_framework.create_orchestrator()

        # Use a query with clear SIMPLE keywords
        query = "What is the purpose of the main function?"

        # Configure only solving LLM response (no assessment LLM needed)
        solving_response = MockLLMResponse(
            content="The main function is the entry point.",
            input_tokens=100,
            output_tokens=20,
        )
        e2e_framework.mock_llm.configure_response("purpose", solving_response)

        # Execute query
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify assessment completed
        assert "phase1_assess" in response["metadata"]["phases"]
        assess_meta = response["metadata"]["phases"]["phase1_assess"]

        # Check that assessment identified as SIMPLE
        assert assess_meta["complexity"] == "SIMPLE"
        assert assess_meta["method"] in ["keyword", "llm"]

        # Verify response succeeded
        assert response["confidence"] > 0

    def test_simple_query_with_context_retrieval(self, e2e_framework):
        """Test that simple queries retrieve appropriate context."""
        # Add some test chunks to the store
        from aurora_core.chunks.code_chunk import CodeChunk

        test_chunk = CodeChunk(
            chunk_id="code:test.py:hello",
            file_path="/absolute/path/test.py",
            element_type="function",
            name="hello",
            line_start=1,
            line_end=1,
            signature="def hello()",
            docstring="Returns 'world'",
        )
        e2e_framework.store.save_chunk(test_chunk)

        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="The hello function returns 'world'.",
            input_tokens=150,
            output_tokens=20,
        )
        e2e_framework.mock_llm.configure_response("hello", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        # Execute query that should retrieve context
        query = "What does the hello function do?"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify retrieval phase executed
        assert "phase2_retrieve" in response["metadata"]["phases"]
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]

        # Verify context was retrieved
        assert "total_retrieved" in retrieve_meta
        assert retrieve_meta["budget"] == 5

        # Verify response completed
        assert "answer" in response

    def test_simple_query_error_handling(self, e2e_framework):
        """Test error handling in simple query path."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        # Don't configure solving LLM response - should use default
        orchestrator = e2e_framework.create_orchestrator()

        query = "Test error handling"

        # Execute should not crash, should handle gracefully
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify response returned (even if with error)
        assert "answer" in response
        assert "metadata" in response

    def test_simple_query_metadata_completeness(self, e2e_framework):
        """Test that simple query responses include complete metadata."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="Complete metadata test.",
            input_tokens=100,
            output_tokens=15,
        )
        e2e_framework.mock_llm.configure_response("metadata", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        query = "Test metadata completeness"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify metadata structure
        assert "metadata" in response
        metadata = response["metadata"]

        # Check required metadata fields
        assert "total_duration_ms" in metadata
        assert "total_cost_usd" in metadata
        assert "phases" in metadata
        assert "query_id" in metadata

        # Check phase metadata
        assert "phase1_assess" in metadata["phases"]
        assert "phase2_retrieve" in metadata["phases"]
        assert "phase9_respond" in metadata["phases"]

        # Verify timing information
        assert metadata["total_duration_ms"] > 0

    def test_simple_query_confidence_scoring(self, e2e_framework):
        """Test that simple queries return appropriate confidence scores."""
        # Configure responses with varying confidence
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="High confidence response.",
            input_tokens=100,
            output_tokens=15,
        )
        e2e_framework.mock_llm.configure_response("confidence", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        query = "What is high confidence?"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify confidence included
        assert "confidence" in response
        assert 0 <= response["confidence"] <= 1

        # Simple queries should have reasonable confidence
        # (not testing exact value as it depends on implementation)
        assert response["confidence"] >= 0


class TestSimpleQueryEdgeCases:
    """Test edge cases for simple query processing."""

    def test_borderline_simple_assessment(self, e2e_framework):
        """Test query on borderline between SIMPLE and MEDIUM complexity."""
        # Configure LLM to return SIMPLE after borderline keyword match
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.75)

        solving_response = MockLLMResponse(
            content="Borderline complexity response.",
            input_tokens=150,
            output_tokens=25,
        )
        e2e_framework.mock_llm.configure_response("borderline", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        # Use a query that might be borderline
        query = "Explain how the authentication system validates user tokens"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Should complete successfully regardless of assessment method
        assert "answer" in response
        assert "metadata" in response
        assert "phase1_assess" in response["metadata"]["phases"]

    def test_very_short_simple_query(self, e2e_framework):
        """Test very short simple queries."""
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.98)

        solving_response = MockLLMResponse(
            content="Short answer.",
            input_tokens=50,
            output_tokens=5,
        )
        e2e_framework.mock_llm.configure_response("status", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        # Very short query that has SIMPLE keywords
        query = "Show status"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Should handle gracefully
        assert "answer" in response
        assert response["metadata"]["phases"]["phase1_assess"]["complexity"] == "SIMPLE"

    def test_simple_query_with_no_context(self, e2e_framework):
        """Test simple query when no relevant context is found."""
        # Empty store - no context available
        e2e_framework.configure_assessment_response(complexity="SIMPLE", confidence=0.95)

        solving_response = MockLLMResponse(
            content="No context available, general response.",
            input_tokens=100,
            output_tokens=20,
        )
        e2e_framework.mock_llm.configure_response("context", solving_response)

        orchestrator = e2e_framework.create_orchestrator()

        query = "What is the context?"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Should complete successfully even without context
        assert "answer" in response
        assert "phase2_retrieve" in response["metadata"]["phases"]

        # Verify no chunks retrieved
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]
        assert retrieve_meta.get("chunks_retrieved", 0) == 0
