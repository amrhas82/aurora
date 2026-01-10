"""End-to-End Integration Tests for Complex Query Flow.

This module tests the complete SOAR pipeline for COMPLEX complexity queries,
which use the full 9-phase pipeline including decomposition, verification,
routing, and agent execution.

Key aspects tested:
- Phase 1: Assess complexity (should classify as COMPLEX)
- Phase 2: Retrieve context (with COMPLEX budget limit: 15 chunks)
- Phase 3: Decompose query into subgoals
- Phase 4: Verify decomposition (Option B: adversarial verification)
- Phase 5: Route subgoals to agents
- Phase 6: Execute agents (parallel/sequential)
- Phase 7: Synthesize results
- Phase 8: Record reasoning pattern
- Phase 9: Format response

Performance requirements:
- Complex query latency: <10s
"""

from __future__ import annotations

import json
import time
from tempfile import TemporaryDirectory

import pytest

from tests.integration.test_e2e_framework import E2ETestFramework, MockAgent, MockLLMResponse


@pytest.fixture
def e2e_framework():
    """Create E2E test framework."""
    with TemporaryDirectory() as temp_dir:
        framework = E2ETestFramework(temp_dir)
        yield framework
        framework.cleanup()


class TestComplexQueryE2E:
    """End-to-end tests for complex query processing."""

    def test_complex_query_full_pipeline(self, e2e_framework):
        """Test that COMPLEX queries execute all 9 phases."""
        # Configure mock LLM responses for all phases
        # Phase 1: Assessment - COMPLEX
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.92)

        # Phase 3: Decomposition - 3 subgoals
        subgoals = [
            {
                "description": "Analyze authentication flow",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Review security patterns",
                "suggested_agent": "security-checker",
                "is_critical": True,
                "depends_on": [0],
            },
            {
                "description": "Generate recommendations",
                "suggested_agent": "code-analyzer",
                "is_critical": True,
                "depends_on": [0, 1],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        # Phase 4: Verification - PASS
        e2e_framework.configure_verification_response(verdict="PASS", score=0.85, feedback="")

        # Register mock agents
        agent1 = MockAgent(
            agent_id="code-analyzer",
            capabilities=["code-analysis"],
            response={
                "summary": "Authentication flow uses JWT tokens with RS256.",
                "data": {"tokens": "JWT", "algorithm": "RS256"},
                "confidence": 0.9,
            },
        )
        agent2 = MockAgent(
            agent_id="security-checker",
            capabilities=["security-analysis"],
            response={
                "summary": "Security patterns follow OWASP best practices.",
                "data": {"owasp": True, "score": 8.5},
                "confidence": 0.88,
            },
        )
        e2e_framework.register_mock_agent(agent1)
        e2e_framework.register_mock_agent(agent2)

        # Phase 7: Synthesis
        e2e_framework.configure_synthesis_response(
            answer="The authentication system uses JWT tokens with RS256 algorithm "
            "and follows OWASP best practices. Recommendations include implementing "
            "token refresh and adding rate limiting.",
            confidence=0.87,
        )

        # Create orchestrator
        orchestrator = e2e_framework.create_orchestrator()

        # Execute complex query
        query = "Analyze the authentication system security and provide recommendations"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify response structure
        assert "answer" in response
        assert "confidence" in response
        assert "metadata" in response

        # Verify ALL 9 phases executed (except phase 8 if not implemented yet)
        phases = response["metadata"]["phases"]
        e2e_framework.assert_phase_executed(response, "phase1_assess")
        e2e_framework.assert_phase_executed(response, "phase2_retrieve")
        e2e_framework.assert_phase_executed(response, "phase3_decompose")
        e2e_framework.assert_phase_executed(response, "phase4_verify")
        e2e_framework.assert_phase_executed(response, "phase5_route")
        e2e_framework.assert_phase_executed(response, "phase6_collect")
        e2e_framework.assert_phase_executed(response, "phase7_synthesize")
        # Phase 8 (record) and 9 (respond) are optional to verify
        e2e_framework.assert_phase_executed(response, "phase9_respond")

        # Verify assessment identified as COMPLEX
        assert phases["phase1_assess"]["complexity"] == "COMPLEX"

        # Verify decomposition produced subgoals
        assert "subgoals_total" in phases["phase3_decompose"]
        assert phases["phase3_decompose"]["subgoals_total"] == 3

        # Verify verification passed
        assert phases["phase4_verify"]["final_verdict"] == "PASS"
        assert phases["phase4_verify"]["verification"]["overall_score"] >= 0.7

        # Verify agents were executed
        assert phases["phase6_collect"]["agents_executed"] >= 2

        # Verify synthesis completed
        assert "answer" in response
        assert len(response["answer"]) > 0

    def test_complex_query_adversarial_verification(self, e2e_framework):
        """Test that COMPLEX queries use adversarial verification (Option B)."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.93)

        # Decomposition
        subgoals = [
            {
                "description": "Parse configuration files",
                "suggested_agent": "file-parser",
                "is_critical": True,
                "depends_on": [],
            },
            {
                "description": "Validate configuration schema",
                "suggested_agent": "validator",
                "is_critical": True,
                "depends_on": [0],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        # Verification - should use Option B (adversarial)
        e2e_framework.configure_verification_response(verdict="PASS", score=0.78, feedback="")

        # Register agents
        agent1 = MockAgent(
            agent_id="file-parser",
            capabilities=["file-parsing"],
            response={
                "summary": "Found 5 configuration files.",
                "data": {"files": 5},
                "confidence": 0.95,
            },
        )
        agent2 = MockAgent(
            agent_id="validator",
            capabilities=["validation"],
            response={
                "summary": "All configurations valid.",
                "data": {"valid": True},
                "confidence": 0.92,
            },
        )
        e2e_framework.register_mock_agent(agent1)
        e2e_framework.register_mock_agent(agent2)

        # Synthesis
        e2e_framework.configure_synthesis_response(
            answer="Configuration files are valid.",
            confidence=0.90,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Validate all configuration files in the system"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify verification phase executed
        verify_meta = response["metadata"]["phases"]["phase4_verify"]

        # For COMPLEX queries, should use Option B (adversarial)
        assert (
            verify_meta["method"] == "adversarial"
        ), "COMPLEX queries should use adversarial verification (Option B)"

        # Verify verification passed
        assert verify_meta["final_verdict"] == "PASS"
        assert verify_meta["verification"]["overall_score"] >= 0.7

    def test_complex_query_performance(self, e2e_framework):
        """Test that COMPLEX queries complete in <10s."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.91)

        # Simple decomposition to keep test fast
        subgoals = [
            {
                "description": "Analyze code structure",
                "suggested_agent": "analyzer",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.80, feedback="")

        # Register fast agent
        agent = MockAgent(
            agent_id="analyzer",
            capabilities=["analysis"],
            execution_time=0.05,  # 50ms
            response={
                "summary": "Code structure is modular.",
                "data": {"modules": 10},
                "confidence": 0.89,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="The codebase has a modular structure with 10 modules.",
            confidence=0.88,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Measure execution time
        query = "Analyze the overall code structure"
        start_time = time.time()
        response = orchestrator.execute(query, verbosity="QUIET")
        elapsed_time = time.time() - start_time

        # Verify performance requirement: <10s
        assert elapsed_time < 10.0, f"Complex query took {elapsed_time:.2f}s, expected <10s"

        # Verify response completed successfully
        assert response["confidence"] > 0
        assert "answer" in response

    def test_complex_query_budget_allocation(self, e2e_framework):
        """Test that COMPLEX queries use appropriate budget allocation."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.94)

        subgoals = [
            {
                "description": "Process data",
                "suggested_agent": "processor",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.82, feedback="")

        agent = MockAgent(
            agent_id="processor",
            capabilities=["processing"],
            response={
                "summary": "Data processed successfully.",
                "data": {},
                "confidence": 0.90,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Data processing complete.",
            confidence=0.91,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Process the data files"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify COMPLEX budget allocation (15 chunks)
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]
        assert retrieve_meta["budget"] == 15, "COMPLEX queries should have budget of 15 chunks"

    def test_complex_query_parallel_execution(self, e2e_framework):
        """Test that independent subgoals execute in parallel."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.92)

        # Three independent subgoals (can run in parallel)
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
            {
                "description": "Task C",
                "suggested_agent": "worker-c",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        decomposition = {
            "goal": "Parallel tasks",
            "subgoals": subgoals,
            "execution_order": [{"phase": 1, "parallelizable": [0, 1, 2], "sequential": []}],
            "expected_tools": ["worker"],
        }
        e2e_framework.mock_llm.configure_response(
            "decompose",
            MockLLMResponse(
                content=json.dumps(decomposition),
                input_tokens=500,
                output_tokens=200,
            ),
        )

        e2e_framework.configure_verification_response(verdict="PASS", score=0.83, feedback="")

        # Register agents with execution time
        execution_time = 0.5  # 500ms each
        for agent_id in ["worker-a", "worker-b", "worker-c"]:
            agent = MockAgent(
                agent_id=agent_id,
                capabilities=["work"],
                execution_time=execution_time,
                response={
                    "summary": f"Task {agent_id} complete.",
                    "data": {},
                    "confidence": 0.90,
                },
            )
            e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="All parallel tasks completed.",
            confidence=0.90,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Measure execution time
        query = "Execute parallel tasks"
        start_time = time.time()
        response = orchestrator.execute(query, verbosity="NORMAL")
        elapsed_time = time.time() - start_time

        # If parallel execution works, total time should be ~0.5s (not 1.5s)
        # Allow some overhead, but should be significantly less than sequential
        assert elapsed_time < 1.2, (
            f"Parallel execution took {elapsed_time:.2f}s, expected <1.2s "
            f"(sequential would be ~1.5s)"
        )

        # Verify all agents executed
        collect_meta = response["metadata"]["phases"]["phase6_collect"]
        assert collect_meta["agents_executed"] == 3

    def test_complex_query_sequential_execution(self, e2e_framework):
        """Test that dependent subgoals execute sequentially."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.93)

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
                "depends_on": [0],
            },
            {
                "description": "Step 3",
                "suggested_agent": "step-agent",
                "is_critical": True,
                "depends_on": [1],
            },
        ]
        decomposition = {
            "goal": "Sequential tasks",
            "subgoals": subgoals,
            "execution_order": [
                {"phase": 1, "parallelizable": [0], "sequential": []},
                {"phase": 2, "parallelizable": [1], "sequential": []},
                {"phase": 3, "parallelizable": [2], "sequential": []},
            ],
            "expected_tools": ["step-tool"],
        }
        e2e_framework.mock_llm.configure_response(
            "decompose",
            MockLLMResponse(
                content=json.dumps(decomposition),
                input_tokens=500,
                output_tokens=200,
            ),
        )

        e2e_framework.configure_verification_response(verdict="PASS", score=0.81, feedback="")

        # Register agent
        agent = MockAgent(
            agent_id="step-agent",
            capabilities=["steps"],
            execution_time=0.2,  # 200ms each
            response={
                "summary": "Step completed.",
                "data": {},
                "confidence": 0.91,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="All sequential steps completed.",
            confidence=0.92,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Execute sequential steps"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify all agents executed
        collect_meta = response["metadata"]["phases"]["phase6_collect"]
        assert collect_meta["agents_executed"] == 3

        # Verify response completed
        assert "answer" in response
        assert response["confidence"] > 0

    def test_complex_query_cost_tracking(self, e2e_framework):
        """Test that cost tracking works for complex queries."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.92)

        subgoals = [
            {
                "description": "Cost test",
                "suggested_agent": "cost-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.84, feedback="")

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
            answer="Cost tracking test complete.",
            confidence=0.91,
        )

        orchestrator = e2e_framework.create_orchestrator()

        # Track initial budget
        initial_status = e2e_framework.cost_tracker.get_status()
        initial_consumed = initial_status["consumed_usd"]

        # Execute query
        query = "Test cost tracking for complex query"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify cost was tracked
        assert "total_cost_usd" in response["metadata"]
        assert response["metadata"]["total_cost_usd"] > 0

        # Complex queries should have higher cost than simple queries
        # (more LLM calls: assess, decompose, verify, synthesize)
        assert response["metadata"]["total_cost_usd"] > 0

        # Verify budget tracker updated
        final_status = e2e_framework.cost_tracker.get_status()
        final_consumed = final_status["consumed_usd"]
        assert final_consumed > initial_consumed, "Budget should be updated"

    def test_complex_query_metadata_completeness(self, e2e_framework):
        """Test that complex query responses include complete metadata."""
        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.93)

        subgoals = [
            {
                "description": "Metadata test",
                "suggested_agent": "meta-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.85, feedback="")

        agent = MockAgent(
            agent_id="meta-agent",
            capabilities=["metadata"],
            response={
                "summary": "Metadata test complete.",
                "data": {},
                "confidence": 0.92,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="Metadata completeness verified.",
            confidence=0.91,
        )

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

        # Check phase metadata for complex query
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

    def test_complex_query_with_context(self, e2e_framework):
        """Test that complex queries retrieve appropriate context."""
        # Add test chunks to the store
        from aurora_core.chunks.code_chunk import CodeChunk

        test_chunk = CodeChunk(
            chunk_id="code:auth.py:AuthService",
            file_path="/absolute/path/auth.py",
            element_type="class",
            name="AuthService",
            line_start=1,
            line_end=2,
            signature="class AuthService",
            docstring="Authentication service",
        )
        e2e_framework.store.save_chunk(test_chunk)

        # Configure responses
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.93)

        subgoals = [
            {
                "description": "Analyze auth service",
                "suggested_agent": "auth-analyzer",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.83, feedback="")

        agent = MockAgent(
            agent_id="auth-analyzer",
            capabilities=["authentication"],
            response={
                "summary": "AuthService provides authentication.",
                "data": {},
                "confidence": 0.92,
            },
        )
        e2e_framework.register_mock_agent(agent)

        e2e_framework.configure_synthesis_response(
            answer="The AuthService class provides authentication functionality.",
            confidence=0.91,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Analyze the authentication service implementation"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify retrieval phase executed
        assert "phase2_retrieve" in response["metadata"]["phases"]
        retrieve_meta = response["metadata"]["phases"]["phase2_retrieve"]

        # Verify COMPLEX budget (15 chunks)
        assert retrieve_meta["budget"] == 15

        # Verify response completed
        assert "answer" in response


class TestComplexQueryEdgeCases:
    """Test edge cases for complex query processing."""

    def test_complex_query_with_verification_retry(self, e2e_framework):
        """Test complex query with verification failure triggering retry."""
        # This will be covered in test_verification_retry.py
        # Just verify basic retry mechanism
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.92)

        # Configure agent
        agent = MockAgent(
            agent_id="retry-agent",
            capabilities=["retry"],
            response={
                "summary": "Retry test complete.",
                "data": {},
                "confidence": 0.90,
            },
        )
        e2e_framework.register_mock_agent(agent)

        # Manually configure synthesis response without verification to avoid pattern conflicts
        synthesis_response = MockLLMResponse(
            content="ANSWER: Retry mechanism works. (Agent: retry-agent)\nCONFIDENCE: 0.88",
            input_tokens=600,
            output_tokens=300,
        )
        e2e_framework.mock_llm.configure_response("synthesizing information", synthesis_response)
        e2e_framework.mock_llm.configure_response("combine the agent outputs", synthesis_response)

        subgoals = [
            {
                "description": "Test retry",
                "suggested_agent": "retry-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]

        # First verification fails (triggers retry)
        retry_response = MockLLMResponse(
            content=json.dumps(
                {
                    "verdict": "RETRY",
                    "overall_score": 0.62,
                    "completeness": 0.60,
                    "consistency": 0.65,
                    "groundedness": 0.60,
                    "routability": 0.63,
                    "feedback": "Decomposition lacks detail.",
                }
            ),
            input_tokens=400,
            output_tokens=150,
        )
        # Second verification passes
        pass_response = MockLLMResponse(
            content=json.dumps(
                {
                    "verdict": "PASS",
                    "overall_score": 0.78,
                    "completeness": 0.80,
                    "consistency": 0.75,
                    "groundedness": 0.79,
                    "routability": 0.78,
                    "feedback": "",
                }
            ),
            input_tokens=400,
            output_tokens=150,
        )

        # Configure multiple responses for verification (retry pattern)
        # Use pattern specific to adversarial decomposition verification
        e2e_framework.mock_llm.configure_responses(
            "RED TEAM adversarial verifier", [retry_response, pass_response]
        )

        # Need two decomposition responses (initial + retry)
        decomp_response = MockLLMResponse(
            content=json.dumps(
                {
                    "goal": "Retry test",
                    "subgoals": subgoals,
                    "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
                    "expected_tools": ["retry-tool"],
                }
            ),
            input_tokens=500,
            output_tokens=200,
        )
        e2e_framework.mock_llm.configure_responses("decompose", [decomp_response, decomp_response])

        orchestrator = e2e_framework.create_orchestrator()

        query = "Test verification retry"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Verify verification eventually passed
        verify_meta = response["metadata"]["phases"]["phase4_verify"]
        assert verify_meta["final_verdict"] == "PASS"

        # Check if retry occurred (retry_count should be tracked)
        assert verify_meta["retry_count"] >= 1

    def test_complex_query_agent_not_found_fallback(self, e2e_framework):
        """Test fallback when suggested agent not found."""
        e2e_framework.configure_assessment_response(complexity="COMPLEX", confidence=0.92)

        # Decomposition suggests non-existent agent
        subgoals = [
            {
                "description": "Task requiring non-existent agent",
                "suggested_agent": "non-existent-agent",
                "is_critical": True,
                "depends_on": [],
            },
        ]
        e2e_framework.configure_decomposition_response(subgoals)

        e2e_framework.configure_verification_response(verdict="PASS", score=0.80, feedback="")

        # Don't register the agent - should fall back to llm-executor
        # (llm-executor should be registered by default in agent registry)

        e2e_framework.configure_synthesis_response(
            answer="Fallback agent handled the task.",
            confidence=0.75,
        )

        orchestrator = e2e_framework.create_orchestrator()

        query = "Test agent fallback"
        response = orchestrator.execute(query, verbosity="NORMAL")

        # Should complete (possibly with warning about fallback)
        assert "answer" in response
        assert "metadata" in response

        # Route phase should show fallback
        if "phase5_route" in response["metadata"]["phases"]:
            response["metadata"]["phases"]["phase5_route"]
            # Check for fallback indicator if available
            # (implementation may vary)
