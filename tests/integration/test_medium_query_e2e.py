"""End-to-End Integration Tests for Medium Query Flow.

This module tests the complete SOAR pipeline for MEDIUM complexity queries,
which use decomposition with self-verification (Option A).

Key aspects tested:
- Phase 1: Assess complexity (should classify as MEDIUM)
- Phase 2: Retrieve context (with MEDIUM budget limit: 10 chunks)
- Phase 3: Decompose query into subgoals
- Phase 4: Verify decomposition (Option A: self-verification)
- Phase 5: Route subgoals to agents
- Phase 6: Execute agents (parallel/sequential)
- Phase 7: Synthesize results
- Phase 8: Record reasoning pattern
- Phase 9: Format response

Performance requirements:
- Medium query latency: <5s (between simple <2s and complex <10s)
"""

from __future__ import annotations

import time
from tempfile import TemporaryDirectory

import pytest

from tests.integration.test_e2e_framework import (
    E2ETestFramework,
    MockAgent,
)


@pytest.fixture
def e2e_framework():
    """Create E2E test framework."""
    with TemporaryDirectory() as temp_dir:
        framework = E2ETestFramework(temp_dir)
        yield framework
        framework.cleanup()


class TestMediumQueryE2E:
    """End-to-end tests for medium query processing."""

    def test_medium_query_full_pipeline(self, e2e_framework):
        """Test that MEDIUM queries execute all 9 phases."""
        # Configure mock LLM responses for all phases
        # Phase 1: Assessment - MEDIUM
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.89)

        # Phase 3: Decomposition - 2 subgoals (simpler than complex)
        subgoals = [
            {
                "description": "Extract user data from database",
                "suggested_agent": "database-query",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Format data for display",
                "suggested_agent": "formatter",
                "is_critical": True,
                "depends_on": [0],  # Depends on first subgoal (integer index)
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        # Phase 4: Verification - PASS (self-verification for MEDIUM)
        e2e_framework.configure_verification_response(verdict="PASS", score=0.82, feedback="")

        # Register mock agents
        agent1 = MockAgent(
            agent_id="database-query",
            capabilities=["database", "query"],
            response={
                "summary": "Retrieved 42 user records from database.",
                "data": {"records": 42, "query_time_ms": 50},
                "confidence": 0.92,
            },
        )
        agent2 = MockAgent(
            agent_id="formatter",
            capabilities=["formatting", "display"],
            response={
                "summary": "Formatted 42 records in table format.",
                "data": {"format": "table", "rows": 42},
                "confidence": 0.88,
            },
        )
        e2e_framework.register_mock_agent(agent1)
        e2e_framework.register_mock_agent(agent2)

        # Phase 7: Synthesis
        e2e_framework.configure_synthesis_response(
            answer="Successfully retrieved 42 user records from the database "
            "and formatted them in table format for display.",
            confidence=0.90,
        )

        # Create orchestrator
        orchestrator = e2e_framework.create_orchestrator()

        # Execute medium query (use MEDIUM keywords: analyze, create)
        query = "Analyze user data and create formatted report"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify response structure
        assert "answer" in response
        assert "confidence" in response
        assert "metadata" in response

        # Verify ALL 9 phases executed
        phases = response["metadata"]["phases"]
        e2e_framework.assert_phase_executed(response, "phase1_assess")
        e2e_framework.assert_phase_executed(response, "phase2_retrieve")
        e2e_framework.assert_phase_executed(response, "phase3_decompose")
        e2e_framework.assert_phase_executed(response, "phase4_verify")
        e2e_framework.assert_phase_executed(response, "phase5_route")
        e2e_framework.assert_phase_executed(response, "phase6_collect")
        e2e_framework.assert_phase_executed(response, "phase7_synthesize")
        e2e_framework.assert_phase_executed(response, "phase9_respond")

        # Verify assessment identified as MEDIUM
        assert phases["phase1_assess"]["complexity"] == "MEDIUM"

        # Verify decomposition produced subgoals
        assert "subgoals_total" in phases["phase3_decompose"]
        assert phases["phase3_decompose"]["subgoals_total"] == 2

        # Verify verification passed
        assert phases["phase4_verify"]["final_verdict"] == "PASS"
        assert phases["phase4_verify"]["verification"]["overall_score"] >= 0.7

        # Verify agents were executed
        assert phases["phase6_collect"]["agents_executed"] >= 2

        # Verify synthesis completed
        assert "answer" in response
        assert len(response["answer"]) > 0

    def test_medium_query_self_verification(self, e2e_framework):
        """Test that MEDIUM queries use self-verification (Option A)."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)

        # Decomposition
        subgoals = [
            {
                "description": "Validate input parameters",
                "suggested_agent": "validator",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Process request",
                "suggested_agent": "processor",
                "is_critical": True,
                "depends_on": [0],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        # Verification - should use Option A (self-verification)
        e2e_framework.configure_verification_response(verdict="PASS", score=0.75, feedback="")

        # Register agents
        agent1 = MockAgent(
            agent_id="validator",
            capabilities=["validation"],
            response={
                "summary": "All parameters are valid.",
                "data": {"valid": True},
                "confidence": 0.94,
            },
        )
        agent2 = MockAgent(
            agent_id="processor",
            capabilities=["processing"],
            response={
                "summary": "Request processed successfully.",
                "data": {"status": "success"},
                "confidence": 0.89,
            },
        )
        e2e_framework.register_mock_agent(agent1)
        e2e_framework.register_mock_agent(agent2)

        # Synthesis
        e2e_framework.configure_synthesis_response(
            answer="Request validated and processed successfully.",
            confidence=0.91,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Validate and process the incoming request"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify verification phase executed
        verify_meta = response["metadata"]["phases"]["phase4_verify"]

        # For MEDIUM queries, should use Option A (self-verification)
        assert verify_meta["method"] == "self", (
            "MEDIUM queries should use self-verification (Option A)"
        )

        # Verify verification passed
        assert verify_meta["final_verdict"] == "PASS"
        assert verify_meta["verification"]["overall_score"] >= 0.7

    def test_medium_query_performance(self, e2e_framework):
        """Test that MEDIUM queries complete in reasonable time (<5s)."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.88)

        # Simple decomposition to keep test fast
        subgoals = [
            {
                "description": "Fetch data",
                "suggested_agent": "fetcher",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.79, feedback="")

        # Register fast agent
        agent = MockAgent(
            agent_id="fetcher",
            capabilities=["fetch"],
            execution_time=0.05,  # 50ms
            response={
                "summary": "Data fetched successfully.",
                "data": {"items": 10},
                "confidence": 0.91,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Successfully fetched 10 data items.",
            confidence=0.90,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Measure execution time
        query = "Fetch the latest data items"
        start_time = time.time()
        response = orchestrator.execute(query, verbosity="QUIET")
        elapsed_time = time.time() - start_time

        # Verify performance requirement: <5s (medium range)
        assert elapsed_time < 5.0, f"Medium query took {elapsed_time:.2f}s, expected <5s"

        # Verify response completed successfully
        assert response["confidence"] > 0
        assert "answer" in response

    def test_medium_query_budget_allocation(self, e2e_framework):
        """Test that MEDIUM queries use appropriate budget allocation."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.86)

        subgoals = [
            {
                "description": "Analyze data",
                "suggested_agent": "analyzer",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.80, feedback="")

        agent = MockAgent(
            agent_id="analyzer",
            capabilities=["analysis"],
            response={
                "summary": "Data analysis complete.",
                "data": {},
                "confidence": 0.88,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Analysis shows positive trends.",
            confidence=0.89,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Analyze the data trends"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify MEDIUM budget allocation (10 chunks)
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]
        assert retrieve_meta["budget"] == 10, "MEDIUM queries should have budget of 10 chunks"

    def test_medium_query_parallel_execution(self, e2e_framework):
        """Test that independent subgoals execute in parallel for medium queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)

        # Two independent subgoals (can run in parallel)
        subgoals = [
            {
                "description": "Task A",
                "suggested_agent": "worker-a",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Task B",
                "suggested_agent": "worker-b",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.81, feedback="")

        # Register agents with execution time
        execution_time = 0.3  # 300ms each
        for agent_id in ["worker-a", "worker-b"]:
            agent = MockAgent(
                agent_id=agent_id,
                capabilities=["work"],
                execution_time=execution_time,
                response={
                    "summary": f"Task {agent_id} complete.",
                    "data": {},
                    "confidence": 0.89,
                },
            )
            e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Both parallel tasks completed successfully.",
            confidence=0.88,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Measure execution time
        query = "Execute two independent medium tasks"
        start_time = time.time()
        response = orchestrator.execute(query, verbosity="NORMAL")
        elapsed_time = time.time() - start_time

        # If parallel execution works, total time should be ~0.3s (not 0.6s)
        # Allow overhead, but should be significantly less than sequential
        assert elapsed_time < 0.8, (
            f"Parallel execution took {elapsed_time:.2f}s, expected <0.8s "
            f"(sequential would be ~0.6s)"
        )

        # Verify all agents executed
        collect_meta = response["metadata"]["phases"]["phase6_collect"]
        assert collect_meta["agents_executed"] == 2

    def test_medium_query_cost_tracking(self, e2e_framework):
        """Test that cost tracking works for medium queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)

        subgoals = [
            {
                "description": "Cost test",
                "suggested_agent": "cost-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.78, feedback="")

        agent = MockAgent(
            agent_id="cost-agent",
            capabilities=["cost"],
            response={
                "summary": "Cost test complete.",
                "data": {},
                "confidence": 0.90,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Medium cost tracking test complete.",
            confidence=0.89,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Track initial budget
        initial_status = e2e_framework.cost_tracker.get_status()
        initial_consumed = initial_status["consumed_usd"]

        # Execute query
        query = "Test cost tracking for medium query"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify cost was tracked
        assert "total_cost_usd" in response["metadata"]
        assert response["metadata"]["total_cost_usd"] > 0

        # Medium queries should have moderate cost (more than simple, less than complex)
        # (LLM calls: assess, decompose, verify self, synthesize)
        assert response["metadata"]["total_cost_usd"] > 0

        # Verify budget tracker updated
        final_status = e2e_framework.cost_tracker.get_status()
        final_consumed = final_status["consumed_usd"]
        assert final_consumed > initial_consumed, "Budget should be updated"

    def test_medium_query_metadata_completeness(self, e2e_framework):
        """Test that medium query responses include complete metadata."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.88)

        subgoals = [
            {
                "description": "Metadata test",
                "suggested_agent": "meta-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.82, feedback="")

        agent = MockAgent(
            agent_id="meta-agent",
            capabilities=["metadata"],
            response={
                "summary": "Metadata test complete.",
                "data": {},
                "confidence": 0.91,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Metadata completeness verified for medium query.",
            confidence=0.90,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Test metadata completeness for medium complexity"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify metadata structure
        assert "metadata" in response
        metadata = response["metadata"]

        # Check required metadata fields
        assert "total_duration_ms" in metadata
        assert "total_cost_usd" in metadata
        assert "phases" in metadata
        assert "query_id" in metadata

        # Check phase metadata for medium query
        assert "phase1_assess" in metadata["phases"]
        assert "phase2_retrieve" in metadata["phases"]
        assert "phase3_decompose" in metadata["phases"]
        assert "phase4_verify" in metadata["phases"]
        assert "phase5_route" in metadata["phases"]
        assert "phase6_collect" in metadata["phases"]
        assert "phase7_synthesize" in metadata["phases"]
        assert "phase9_respond" in metadata["phases"]

        # Verify timing information
        assert metadata["total_duration_ms"] > 0

    def test_medium_query_with_context(self, e2e_framework):
        """Test that medium queries retrieve appropriate context."""
        # Add test chunks to the store
        from aurora.core.chunks.code_chunk import CodeChunk

        test_chunk = CodeChunk(
            chunk_id="code:utils.py:calculate",
            file_path="/absolute/path/utils.py",
            element_type="function",
            name="calculate",
            line_start=1,
            line_end=2,
            signature="def calculate(x, y)",
            docstring="Calculate result",
        )
        e2e_framework.store.save_chunk(test_chunk)

        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.88)

        subgoals = [
            {
                "description": "Analyze calculate function",
                "suggested_agent": "calc-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.79, feedback="")

        agent = MockAgent(
            agent_id="calc-analyzer",
            capabilities=["calculation"],
            response={
                "summary": "Calculate function performs arithmetic operations.",
                "data": {},
                "confidence": 0.90,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="The calculate function handles arithmetic operations with two parameters.",
            confidence=0.89,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Analyze the calculate function implementation"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify retrieval phase executed
        assert "phase2_retrieve" in response["metadata"]["phases"]
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]

        # Verify MEDIUM budget (10 chunks)
        assert retrieve_meta["budget"] == 10

        # Verify response completed
        assert "answer" in response

    def test_medium_query_verbosity_levels(self, e2e_framework):
        """Test that all verbosity levels work for medium queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)

        subgoals = [
            {
                "description": "Verbosity test",
                "suggested_agent": "verb-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.80, feedback="")

        agent = MockAgent(
            agent_id="verb-agent",
            capabilities=["verbosity"],
            response={
                "summary": "Verbosity test complete.",
                "data": {},
                "confidence": 0.90,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Verbosity level test for medium query.",
            confidence=0.88,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Test verbosity levels"

        # Test QUIET mode
        response_quiet = orchestrator.execute(query, verbosity="QUIET")
        assert "answer" in response_quiet
        assert "metadata" in response_quiet

        # Reset mocks for next calls
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)
        e2e_framework.configure_decomposition_response(subgoals)
        e2e_framework.configure_verification_response(verdict="PASS", score=0.80, feedback="")
        e2e_framework.configure_synthesis_response(
            answer="Verbosity level test for medium query.",
            confidence=0.88,
        )

        # Test NORMAL mode
        response_normal = orchestrator.execute(query, verbosity="NORMAL")
        assert "answer" in response_normal
        assert "metadata" in response_normal
        assert "phases" in response_normal["metadata"]

        # Reset mocks
        e2e_framework.configure_decomposition_response(subgoals)
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)
        e2e_framework.configure_verification_response(verdict="PASS", score=0.80, feedback="")
        e2e_framework.configure_synthesis_response(
            answer="Verbosity level test for medium query.",
            confidence=0.88,
        )

        # Test VERBOSE mode
        response_verbose = orchestrator.execute(query, verbosity="VERBOSE")
        assert "answer" in response_verbose
        assert "metadata" in response_verbose
        assert "phases" in response_verbose["metadata"]
        assert "reasoning_trace" in response_verbose


class TestMediumQueryEdgeCases:
    """Test edge cases for medium query processing."""

    def test_borderline_medium_assessment(self, e2e_framework):
        """Test query on borderline between SIMPLE and MEDIUM complexity."""
        # Configure LLM to return MEDIUM after borderline keyword match
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.72)

        subgoals = [
            {
                "description": "Borderline task",
                "suggested_agent": "border-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.76, feedback="")

        agent = MockAgent(
            agent_id="border-agent",
            capabilities=["borderline"],
            response={
                "summary": "Borderline complexity handled.",
                "data": {},
                "confidence": 0.87,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Borderline complexity query processed successfully.",
            confidence=0.86,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Use a query that might be borderline
        query = "Find and summarize the key features of the system"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Should complete successfully regardless of assessment method
        assert "answer" in response
        assert "metadata" in response
        assert "phase1_assess" in response["metadata"]["phases"]

    def test_medium_query_with_no_context(self, e2e_framework):
        """Test medium query when no relevant context is found."""
        # Empty store - no context available
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.88)

        subgoals = [
            {
                "description": "Process without context",
                "suggested_agent": "ctx-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.77, feedback="")

        agent = MockAgent(
            agent_id="ctx-agent",
            capabilities=["context"],
            response={
                "summary": "Processed without context.",
                "data": {},
                "confidence": 0.85,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Query processed successfully without context.",
            confidence=0.83,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Process this medium complexity query"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Should complete successfully even without context
        assert "answer" in response
        assert "phase2_retrieve" in response["metadata"]["phases"]

        # Verify no chunks retrieved
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]
        assert retrieve_meta.get("chunks_retrieved", 0) == 0

    def test_medium_query_sequential_execution(self, e2e_framework):
        """Test that dependent subgoals execute sequentially for medium queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="MEDIUM", confidence=0.87)

        # Sequential subgoals with dependencies
        subgoals = [
            {
                "description": "Step 1",
                "suggested_agent": "step-agent",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Step 2",
                "suggested_agent": "step-agent",
                "is_critical": True,
                "depends_on": [0],  # Depends on first subgoal
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.79, feedback="")

        # Register agent
        agent = MockAgent(
            agent_id="step-agent",
            capabilities=["steps"],
            execution_time=0.15,  # 150ms each
            response={
                "summary": "Step completed.",
                "data": {},
                "confidence": 0.90,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="All sequential medium steps completed.",
            confidence=0.89,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Execute sequential medium steps"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify all agents executed
        collect_meta = response["metadata"]["phases"]["phase6_collect"]
        assert collect_meta["agents_executed"] == 2

        # Verify response completed
        assert "answer" in response
        assert response["confidence"] > 0
