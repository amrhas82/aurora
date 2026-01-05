"""Unit tests for SOAR phase handlers in AuroraMCPTools.

Tests all 9 phase handler functions for the multi-turn SOAR pipeline:
- assess: Complexity assessment
- retrieve: Context retrieval
- decompose: Query decomposition
- verify: Decomposition verification
- route: Agent routing
- collect: Agent execution
- synthesize: Result synthesis
- record: Pattern caching
- respond: Response formatting
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from aurora_mcp.tools import AuroraMCPTools


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def mock_db_path(tmp_path):
    """Create a temporary database path."""
    db_path = tmp_path / "test_memory.db"
    return str(db_path)


@pytest.fixture
def tools(mock_db_path):
    """Create AuroraMCPTools instance with mocked dependencies."""
    tools = AuroraMCPTools(db_path=mock_db_path)

    # Mock the components to avoid actual database operations
    tools._store = Mock()
    tools._activation_engine = Mock()
    tools._embedding_provider = Mock()
    tools._retriever = Mock()
    tools._memory_manager = Mock()
    tools._parser_registry = Mock()

    return tools


# ========================================================================
# Task 3.1: Assess Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestAssessPhaseHandler:
    """Tests for _handle_assess_phase method."""

    def test_assess_simple_query_returns_early_exit(self, tools):
        """SIMPLE queries should suggest early exit with direct response."""
        with patch('aurora_mcp.tools.assess_complexity') as mock_assess:
            # Mock assess_complexity to return SIMPLE classification
            mock_assess.return_value = {
                'complexity': 'SIMPLE',
                'confidence': 0.9,
                'method': 'keyword',
                'reasoning': 'Keyword-based classification',
                'score': 0.2
            }

            # Mock _retrieve_chunks to return some chunks
            tools._retrieve_chunks = Mock(return_value=[
                {
                    'chunk_id': 'chunk1',
                    'type': 'code',
                    'content': 'def example(): pass',
                    'file_path': '/test.py',
                    'line_range': [1, 2],
                    'relevance_score': 0.9,
                    'name': 'example'
                }
            ])

            result = tools._handle_assess_phase(query="What is Python?", limit=10)

            # Verify response structure
            assert result['phase'] == 'assess'
            assert result['progress'] == '1/9 assess'
            assert result['status'] == 'complete'
            assert 'result' in result
            assert result['result']['complexity'] == 'SIMPLE'
            assert 'Retrieve and respond directly' in result['next_action']

    def test_assess_medium_query_suggests_retrieve(self, tools):
        """MEDIUM queries should suggest calling retrieve phase."""
        with patch('aurora_mcp.tools.assess_complexity') as mock_assess:
            mock_assess.return_value = {
                'complexity': 'MEDIUM',
                'confidence': 0.85,
                'method': 'keyword',
                'reasoning': 'Multi-step query',
                'score': 0.55
            }

            tools._retrieve_chunks = Mock(return_value=[])

            result = tools._handle_assess_phase(query="How does async work?", limit=10)

            assert result['result']['complexity'] == 'MEDIUM'
            assert "phase='retrieve'" in result['next_action']

    def test_assess_complex_query_suggests_retrieve(self, tools):
        """COMPLEX queries should suggest calling retrieve phase."""
        with patch('aurora_mcp.tools.assess_complexity') as mock_assess:
            mock_assess.return_value = {
                'complexity': 'COMPLEX',
                'confidence': 0.9,
                'method': 'keyword',
                'reasoning': 'Multi-system design',
                'score': 0.8
            }

            tools._retrieve_chunks = Mock(return_value=[])

            result = tools._handle_assess_phase(query="Design a distributed system", limit=10)

            assert result['result']['complexity'] == 'COMPLEX'
            assert "phase='retrieve'" in result['next_action']

    def test_assess_critical_query_suggests_retrieve(self, tools):
        """CRITICAL queries should suggest calling retrieve phase."""
        with patch('aurora_mcp.tools.assess_complexity') as mock_assess:
            mock_assess.return_value = {
                'complexity': 'CRITICAL',
                'confidence': 0.95,
                'method': 'keyword',
                'reasoning': 'Security-critical operation',
                'score': 0.9
            }

            tools._retrieve_chunks = Mock(return_value=[])

            result = tools._handle_assess_phase(query="Fix authentication vulnerability", limit=10)

            assert result['result']['complexity'] == 'CRITICAL'
            assert "phase='retrieve'" in result['next_action']

    def test_assess_includes_complexity_score(self, tools):
        """Assess phase should include complexity_score in result."""
        with patch('aurora_mcp.tools.assess_complexity') as mock_assess:
            mock_assess.return_value = {
                'complexity': 'MEDIUM',
                'confidence': 0.8,
                'method': 'keyword',
                'reasoning': 'Test',
                'score': 0.6
            }

            tools._retrieve_chunks = Mock(return_value=[])

            result = tools._handle_assess_phase(query="Test query", limit=10)

            assert 'complexity_score' in result['result']
            assert 'retrieval_confidence' in result['result']

    def test_assess_updates_session_cache(self, tools):
        """Assess phase should update session cache for aurora_get."""
        with patch('aurora_mcp.tools.assess_complexity') as mock_assess:
            mock_assess.return_value = {
                'complexity': 'SIMPLE',
                'confidence': 0.9,
                'method': 'keyword',
                'reasoning': 'Test',
                'score': 0.3
            }

            chunks = [{'chunk_id': 'test', 'content': 'test content'}]
            tools._retrieve_chunks = Mock(return_value=chunks)

            result = tools._handle_assess_phase(query="Test", limit=10)

            assert tools._last_search_results == chunks
            assert tools._last_search_timestamp is not None


# ========================================================================
# Task 3.3: Retrieve Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestRetrievePhaseHandler:
    """Tests for _handle_retrieve_phase method."""

    def test_retrieve_returns_chunks(self, tools):
        """Retrieve phase should return chunks in result."""
        chunks = [
            {'chunk_id': 'chunk1', 'content': 'test content', 'type': 'code'}
        ]
        tools._retrieve_chunks = Mock(return_value=chunks)

        result = tools._handle_retrieve_phase(query="Test query", limit=10)

        assert result['phase'] == 'retrieve'
        assert result['progress'] == '2/9 retrieve'
        assert result['status'] == 'complete'
        assert 'chunks' in result['result']
        assert result['result']['chunks'] == chunks

    def test_retrieve_uses_hybrid_retriever(self, tools):
        """Retrieve phase should use HybridRetriever via _retrieve_chunks."""
        tools._retrieve_chunks = Mock(return_value=[])

        result = tools._handle_retrieve_phase(query="Test", limit=10)

        # Verify _retrieve_chunks was called
        tools._retrieve_chunks.assert_called_once()

    def test_retrieve_updates_session_cache(self, tools):
        """Retrieve phase should update session cache."""
        chunks = [{'chunk_id': 'test'}]
        tools._retrieve_chunks = Mock(return_value=chunks)

        result = tools._handle_retrieve_phase(query="Test", limit=10)

        assert tools._last_search_results == chunks
        assert tools._last_search_timestamp is not None

    def test_retrieve_suggests_decompose_for_complex(self, tools):
        """Retrieve for MEDIUM/COMPLEX should suggest decompose phase."""
        tools._retrieve_chunks = Mock(return_value=[])

        result = tools._handle_retrieve_phase(
            query="Test",
            limit=10,
            complexity="COMPLEX"
        )

        assert "phase='decompose'" in result['next_action']

    def test_retrieve_suggests_respond_for_simple(self, tools):
        """Retrieve for SIMPLE should suggest respond phase."""
        tools._retrieve_chunks = Mock(return_value=[])

        result = tools._handle_retrieve_phase(
            query="Test",
            limit=10,
            complexity="SIMPLE"
        )

        assert "phase='respond'" in result['next_action']


# ========================================================================
# Task 3.5: Decompose Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestDecomposePhaseHandler:
    """Tests for _handle_decompose_phase method."""

    def test_decompose_returns_prompt_template(self, tools):
        """Decompose phase should return prompt template for Claude."""
        pytest.skip("Not implemented yet - Task 3.6")

    def test_decompose_no_llm_calls(self, tools):
        """Decompose phase should NOT make any LLM calls."""
        pytest.skip("Not implemented yet - Task 3.6")

    def test_decompose_accepts_context_parameter(self, tools):
        """Decompose phase should accept context parameter."""
        pytest.skip("Not implemented yet - Task 3.6")

    def test_decompose_suggests_verify_next(self, tools):
        """Decompose phase should suggest verify phase next."""
        pytest.skip("Not implemented yet - Task 3.6")


# ========================================================================
# Task 3.7: Verify Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestVerifyPhaseHandler:
    """Tests for _handle_verify_phase method."""

    def test_verify_requires_subgoals_parameter(self, tools):
        """Verify phase should require subgoals parameter."""
        pytest.skip("Not implemented yet - Task 3.8")

    def test_verify_returns_pass_verdict_for_valid_subgoals(self, tools):
        """Verify phase should return PASS for valid subgoals."""
        pytest.skip("Not implemented yet - Task 3.8")

    def test_verify_returns_fail_verdict_for_invalid_subgoals(self, tools):
        """Verify phase should return FAIL for invalid subgoals."""
        pytest.skip("Not implemented yet - Task 3.8")

    def test_verify_pass_suggests_route(self, tools):
        """Verify PASS should suggest route phase."""
        pytest.skip("Not implemented yet - Task 3.8")

    def test_verify_fail_suggests_retry(self, tools):
        """Verify FAIL should suggest revising decomposition."""
        pytest.skip("Not implemented yet - Task 3.8")


# ========================================================================
# Task 3.9: Route Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestRoutePhaseHandler:
    """Tests for _handle_route_phase method."""

    def test_route_maps_subgoals_to_agents(self, tools):
        """Route phase should map subgoals to available agents."""
        pytest.skip("Not implemented yet - Task 3.10")

    def test_route_accepts_subgoals_parameter(self, tools):
        """Route phase should accept subgoals parameter."""
        pytest.skip("Not implemented yet - Task 3.10")

    def test_route_returns_routing_plan(self, tools):
        """Route phase should return routing plan in result."""
        pytest.skip("Not implemented yet - Task 3.10")

    def test_route_suggests_collect(self, tools):
        """Route phase should suggest collect phase next."""
        pytest.skip("Not implemented yet - Task 3.10")


# ========================================================================
# Task 3.11: Collect Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestCollectPhaseHandler:
    """Tests for _handle_collect_phase method."""

    def test_collect_generates_agent_task_prompts(self, tools):
        """Collect phase should generate task prompts for agents."""
        pytest.skip("Not implemented yet - Task 3.12")

    def test_collect_no_agent_execution(self, tools):
        """Collect phase should NOT execute agents directly."""
        pytest.skip("Not implemented yet - Task 3.12")

    def test_collect_accepts_routing_parameter(self, tools):
        """Collect phase should accept routing parameter."""
        pytest.skip("Not implemented yet - Task 3.12")

    def test_collect_suggests_synthesize(self, tools):
        """Collect phase should suggest synthesize phase next."""
        pytest.skip("Not implemented yet - Task 3.12")


# ========================================================================
# Task 3.13: Synthesize Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestSynthesizePhaseHandler:
    """Tests for _handle_synthesize_phase method."""

    def test_synthesize_returns_prompt_template(self, tools):
        """Synthesize phase should return prompt template."""
        pytest.skip("Not implemented yet - Task 3.14")

    def test_synthesize_accepts_agent_results_parameter(self, tools):
        """Synthesize phase should accept agent_results parameter."""
        pytest.skip("Not implemented yet - Task 3.14")

    def test_synthesize_suggests_record(self, tools):
        """Synthesize phase should suggest record phase next."""
        pytest.skip("Not implemented yet - Task 3.14")


# ========================================================================
# Task 3.15: Record Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestRecordPhaseHandler:
    """Tests for _handle_record_phase method."""

    def test_record_caches_pattern_in_memory(self, tools):
        """Record phase should cache pattern in ACT-R memory."""
        pytest.skip("Not implemented yet - Task 3.16")

    def test_record_accepts_synthesis_parameter(self, tools):
        """Record phase should accept synthesis parameter."""
        pytest.skip("Not implemented yet - Task 3.16")

    def test_record_returns_cache_confirmation(self, tools):
        """Record phase should confirm pattern cached."""
        pytest.skip("Not implemented yet - Task 3.16")

    def test_record_suggests_respond(self, tools):
        """Record phase should suggest respond phase next."""
        pytest.skip("Not implemented yet - Task 3.16")


# ========================================================================
# Task 3.17: Respond Phase Tests (TDD RED phase)
# ========================================================================

@pytest.mark.critical
@pytest.mark.mcp
class TestRespondPhaseHandler:
    """Tests for _handle_respond_phase method."""

    def test_respond_formats_final_answer(self, tools):
        """Respond phase should format final answer."""
        pytest.skip("Not implemented yet - Task 3.18")

    def test_respond_includes_metadata(self, tools):
        """Respond phase should include all metadata."""
        pytest.skip("Not implemented yet - Task 3.18")

    def test_respond_accepts_final_answer_parameter(self, tools):
        """Respond phase should accept final_answer parameter."""
        pytest.skip("Not implemented yet - Task 3.18")

    def test_respond_suggests_present_to_user(self, tools):
        """Respond phase should suggest presenting to user."""
        pytest.skip("Not implemented yet - Task 3.18")
