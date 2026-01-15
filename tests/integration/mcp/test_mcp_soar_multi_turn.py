"""Integration tests for MCP-SOAR multi-turn flow.

This module tests the complete multi-turn SOAR pipeline through the MCP
aurora_query tool with phase parameter, verifying end-to-end orchestration.

Test Coverage:
- SIMPLE query early exit flow (assess → retrieve → respond)
- MEDIUM query full pipeline (all 9 phases)
- COMPLEX query with decomposition
- Phase validation and error handling
- Multi-turn state management
- Response schema validation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurora_mcp.tools import AuroraMCPTools

# Skip all tests in this file - MCP functionality is dormant (PRD-0024)
pytestmark = pytest.mark.skip(reason="MCP functionality dormant - tests deprecated (PRD-0024)")


class TestMCPSOARMultiTurnFlow:
    """Integration tests for MCP-SOAR multi-turn pipeline."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def mcp_tools(self, temp_db):
        """Create AuroraMCPTools instance with mocked dependencies."""
        with patch("aurora_mcp.tools.SQLiteStore"):
            with patch("aurora_mcp.tools.HybridRetriever"):
                tools = AuroraMCPTools(db_path=temp_db)

                # Mock session cache
                tools._session_cache = []

                # Mock retriever
                mock_retriever = MagicMock()
                tools._retriever = mock_retriever

                yield tools

    def test_simple_query_early_exit_flow(self, mcp_tools):
        """Test SIMPLE query flow: assess → retrieve → respond (no decomposition)."""

        # Phase 1: Assess complexity
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {
                "complexity": "SIMPLE",
                "confidence": 0.95,
                "reasons": ["Direct factual question"],
                "early_exit": True,
            }

            result = mcp_tools.aurora_query(query="What is Python?", phase="assess")

            # Verify assess response
            result_data = json.loads(result)
            assert result_data["phase"] == "assess"
            assert result_data["progress"] == "1/9 assess"
            assert result_data["status"] == "complete"
            assert result_data["result"]["complexity"] == "SIMPLE"
            assert result_data["result"]["early_exit"] is True
            assert "retrieve_and_respond" in result_data["next_action"].lower()

        # Phase 2: Retrieve context (mocked)
        with patch.object(mcp_tools, "_retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = [
                {
                    "chunk_id": "chunk-1",
                    "content": "Python is a high-level programming language.",
                    "score": 0.92,
                    "source": "code",
                }
            ]

            result = mcp_tools.aurora_query(query="What is Python?", phase="retrieve")

            # Verify retrieve response
            result_data = json.loads(result)
            assert result_data["phase"] == "retrieve"
            assert result_data["progress"] == "2/9 retrieve"
            assert result_data["status"] == "complete"
            assert len(result_data["result"]["chunks"]) > 0
            assert "respond" in result_data["next_action"].lower()

        # Phase 3: Respond (for SIMPLE, skip decompose/verify/route/collect/synthesize/record)
        with patch("aurora_soar.phases.respond.format_response") as mock_respond:
            mock_respond.return_value = {
                "answer": "Python is a high-level programming language.",
                "metadata": {"complexity": "SIMPLE", "chunks_used": 1},
            }

            result = mcp_tools.aurora_query(
                query="What is Python?",
                phase="respond",
                final_answer="Python is a high-level programming language.",
            )

            # Verify respond response
            result_data = json.loads(result)
            assert result_data["phase"] == "respond"
            assert result_data["progress"] == "9/9 respond"
            assert result_data["status"] == "complete"
            assert "present final answer" in result_data["next_action"].lower()

    def test_medium_query_full_pipeline(self, mcp_tools):
        """Test MEDIUM query flow through all 9 SOAR phases."""

        # Phase 1: Assess
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {
                "complexity": "MEDIUM",
                "confidence": 0.85,
                "reasons": ["Requires multi-step reasoning"],
                "early_exit": False,
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?", phase="assess"
            )

            result_data = json.loads(result)
            assert result_data["result"]["complexity"] == "MEDIUM"
            assert result_data["result"]["early_exit"] is False
            assert "phase='retrieve'" in result_data["next_action"]

        # Phase 2: Retrieve
        with patch.object(mcp_tools, "_retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = [
                {
                    "chunk_id": "c1",
                    "content": "Flask authentication",
                    "score": 0.9,
                    "source": "code",
                }
            ]

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?", phase="retrieve"
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "retrieve"
            assert "phase='decompose'" in result_data["next_action"]

        # Phase 3: Decompose
        with patch("aurora_soar.phases.decompose.generate_decomposition_prompt") as mock_decompose:
            mock_decompose.return_value = {
                "prompt_template": "Break down the query into subgoals...",
                "context_summary": "1 chunks retrieved",
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="decompose",
                context={"chunks": []},
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "decompose"
            assert "prompt_template" in result_data["result"]
            assert "phase='verify'" in result_data["next_action"]

        # Phase 4: Verify
        with patch("aurora_soar.phases.verify.validate_decomposition") as mock_verify:
            mock_verify.return_value = {
                "verdict": "PASS",
                "quality_score": 0.88,
                "feedback": "Decomposition is clear and actionable",
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="verify",
                subgoals=[
                    "Understand Flask-Login library",
                    "Set up user model",
                    "Implement login routes",
                ],
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "verify"
            assert result_data["result"]["verdict"] == "PASS"
            assert "phase='route'" in result_data["next_action"]

        # Phase 5: Route
        with patch("aurora_soar.phases.route.map_subgoals_to_agents") as mock_route:
            mock_route.return_value = {
                "routing_plan": [
                    {"subgoal": "Understand Flask-Login", "agent": "full-stack-dev"},
                    {"subgoal": "Set up user model", "agent": "database-expert"},
                ]
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="route",
                subgoals=["Understand Flask-Login", "Set up user model"],
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "route"
            assert "routing_plan" in result_data["result"]
            assert "phase='collect'" in result_data["next_action"]

        # Phase 6: Collect
        with patch("aurora_soar.phases.collect.generate_agent_tasks") as mock_collect:
            mock_collect.return_value = {
                "agent_tasks": [
                    {"agent": "full-stack-dev", "task_prompt": "Research Flask-Login..."}
                ]
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="collect",
                routing={"routing_plan": []},
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "collect"
            assert "agent_tasks" in result_data["result"]
            assert "phase='synthesize'" in result_data["next_action"]

        # Phase 7: Synthesize
        with patch("aurora_soar.phases.synthesize.generate_synthesis_prompt") as mock_synthesize:
            mock_synthesize.return_value = {
                "prompt_template": "Combine the following agent results...",
                "agent_count": 2,
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="synthesize",
                agent_results=[{"agent": "full-stack-dev", "output": "Use Flask-Login..."}],
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "synthesize"
            assert "prompt_template" in result_data["result"]
            assert "phase='record'" in result_data["next_action"]

        # Phase 8: Record
        with patch("aurora_soar.phases.record.cache_pattern") as mock_record:
            mock_record.return_value = {"pattern_id": "pat-123", "cached": True}

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="record",
                synthesis="Flask authentication guide: 1) Install Flask-Login...",
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "record"
            assert "pattern_id" in result_data["result"]
            assert "phase='respond'" in result_data["next_action"]

        # Phase 9: Respond
        with patch("aurora_soar.phases.respond.format_response") as mock_respond:
            mock_respond.return_value = {
                "answer": "Complete Flask authentication guide...",
                "metadata": {"complexity": "MEDIUM", "phases": 9},
            }

            result = mcp_tools.aurora_query(
                query="How do I implement authentication in Flask?",
                phase="respond",
                final_answer="Complete Flask authentication guide...",
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "respond"
            assert result_data["progress"] == "9/9 respond"
            assert "present final answer" in result_data["next_action"].lower()

    def test_complex_query_with_decomposition(self, mcp_tools):
        """Test COMPLEX query requiring sophisticated decomposition."""

        # Assess as COMPLEX
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {
                "complexity": "COMPLEX",
                "confidence": 0.92,
                "reasons": ["Multi-domain integration", "Performance optimization needed"],
                "early_exit": False,
            }

            result = mcp_tools.aurora_query(
                query="Design a microservices architecture with distributed caching", phase="assess"
            )

            result_data = json.loads(result)
            assert result_data["result"]["complexity"] == "COMPLEX"
            assert len(result_data["result"]["reasons"]) > 0

    def test_phase_validation_error_invalid_phase_name(self, mcp_tools):
        """Test error handling for invalid phase parameter."""

        result = mcp_tools.aurora_query(query="Test query", phase="invalid_phase")

        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert "invalid" in result_data["error"].lower()
        assert "phase" in result_data["error"].lower()

    def test_phase_validation_error_missing_required_parameter(self, mcp_tools):
        """Test error handling when required phase parameters are missing."""

        # Verify phase requires 'subgoals' parameter
        with patch("aurora_soar.phases.verify.validate_decomposition") as mock_verify:
            mock_verify.side_effect = ValueError("Missing required parameter: subgoals")

            result = mcp_tools.aurora_query(
                query="Test query",
                phase="verify",
                # Missing subgoals parameter
            )

            result_data = json.loads(result)
            assert result_data["status"] == "error"
            # Error should mention missing parameter

    def test_verify_phase_rejection_flow(self, mcp_tools):
        """Test verify phase returning FAIL verdict."""

        with patch("aurora_soar.phases.verify.validate_decomposition") as mock_verify:
            mock_verify.return_value = {
                "verdict": "FAIL",
                "quality_score": 0.45,
                "feedback": "Subgoals are too vague and lack actionability",
            }

            result = mcp_tools.aurora_query(
                query="Test query", phase="verify", subgoals=["Do something", "Check stuff"]
            )

            result_data = json.loads(result)
            assert result_data["phase"] == "verify"
            assert result_data["result"]["verdict"] == "FAIL"
            assert "revise" in result_data["next_action"].lower()
            assert "decomposition" in result_data["next_action"].lower()

    def test_end_to_end_timing_metadata(self, mcp_tools):
        """Test that each phase includes timing metadata."""

        # Assess with timing
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {
                "complexity": "MEDIUM",
                "confidence": 0.85,
                "early_exit": False,
            }

            result = mcp_tools.aurora_query(query="Test query", phase="assess")

            result_data = json.loads(result)
            assert "metadata" in result_data
            assert "duration_ms" in result_data["metadata"]
            assert isinstance(result_data["metadata"]["duration_ms"], (int, float))
            assert result_data["metadata"]["duration_ms"] >= 0

    def test_response_schema_validation_all_required_fields(self, mcp_tools):
        """Test that all phases return responses with required schema fields."""

        required_fields = ["phase", "progress", "status", "result", "next_action", "metadata"]

        # Test assess phase response schema
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {
                "complexity": "MEDIUM",
                "confidence": 0.85,
                "early_exit": False,
            }

            result = mcp_tools.aurora_query(query="Test query", phase="assess")

            result_data = json.loads(result)

            # Verify all required fields present
            for field in required_fields:
                assert field in result_data, f"Missing required field: {field}"

            # Verify field types
            assert isinstance(result_data["phase"], str)
            assert isinstance(result_data["progress"], str)
            assert result_data["status"] in ["complete", "error"]
            assert isinstance(result_data["result"], dict)
            assert isinstance(result_data["next_action"], str)
            assert isinstance(result_data["metadata"], dict)

    def test_no_external_llm_calls_during_phases(self, mcp_tools):
        """Test that MCP tools don't make external LLM API calls."""

        # Mock all phase functions to verify no LLM calls
        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.return_value = {"complexity": "SIMPLE", "early_exit": True}

            # Mock LLM client to detect any calls
            with patch("aurora_reasoning.llm_client.LLMClient") as mock_llm:
                mock_llm_instance = MagicMock()
                mock_llm.return_value = mock_llm_instance

                result = mcp_tools.aurora_query(query="Test query", phase="assess")  # noqa: F841

                # Verify LLMClient was never instantiated or called
                assert not mock_llm.called, "MCP tool should not create LLM client"
                assert not mock_llm_instance.called, "MCP tool should not call LLM"

    def test_session_cache_management_across_phases(self, mcp_tools):
        """Test that session cache is properly managed across multi-turn phases."""

        # Phase 1: Retrieve and populate cache
        with patch.object(mcp_tools, "_retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = [
                {"chunk_id": "c1", "content": "Test content", "score": 0.9, "source": "code"}
            ]

            result1 = mcp_tools.aurora_query(query="Test query", phase="retrieve")  # noqa: F841

            # Verify cache was populated
            assert len(mcp_tools._session_cache) > 0

        # Phase 2: Access cache in subsequent phase
        # Cache should persist across phase calls within same session
        initial_cache_size = len(mcp_tools._session_cache)

        with patch("aurora_soar.phases.decompose.generate_decomposition_prompt") as mock_decompose:
            mock_decompose.return_value = {
                "prompt_template": "Decompose based on cached context..."
            }

            result2 = mcp_tools.aurora_query(  # noqa: F841
                query="Test query", phase="decompose", context={"chunks": mcp_tools._session_cache}
            )

            # Cache should be accessible
            assert len(mcp_tools._session_cache) == initial_cache_size


class TestMCPSOARErrorHandling:
    """Integration tests for error handling in MCP-SOAR flow."""

    @pytest.fixture
    def mcp_tools(self):
        """Create AuroraMCPTools instance with mocked dependencies."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        with patch("aurora_mcp.tools.SQLiteStore"):
            with patch("aurora_mcp.tools.HybridRetriever"):
                tools = AuroraMCPTools(db_path=db_path)
                tools._session_cache = []

                yield tools

        Path(db_path).unlink(missing_ok=True)

    def test_graceful_error_handling_phase_function_exception(self, mcp_tools):
        """Test graceful error handling when phase function raises exception."""

        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.side_effect = Exception("Unexpected error in assess phase")

            result = mcp_tools.aurora_query(query="Test query", phase="assess")

            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert "error" in result_data
            # Should include helpful error message
            assert len(result_data["error"]) > 0

    def test_invalid_json_parameter_handling(self, mcp_tools):
        """Test handling of malformed JSON parameters."""

        # Pass invalid structure for context parameter
        with patch("aurora_soar.phases.decompose.generate_decomposition_prompt") as mock_decompose:
            mock_decompose.return_value = {"prompt_template": "test"}

            result = mcp_tools.aurora_query(
                query="Test query", phase="decompose", context="invalid string instead of dict"
            )

            # Should handle gracefully or return error
            result_data = json.loads(result)
            assert "status" in result_data

    def test_missing_dependency_import_error(self, mcp_tools):
        """Test handling when SOAR phase module cannot be imported."""

        with patch("aurora_soar.phases.assess.assess_complexity") as mock_assess:
            mock_assess.side_effect = ImportError("Cannot import assessment module")

            result = mcp_tools.aurora_query(query="Test query", phase="assess")

            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert (
                "import" in result_data["error"].lower() or "module" in result_data["error"].lower()
            )
