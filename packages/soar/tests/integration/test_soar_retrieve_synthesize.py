"""Integration tests for SOAR Retrieve and Synthesize phases.

Tests retrieve_context budget allocation, type-aware retrieval,
error handling, and synthesize_results metadata aggregation.
Uses mocked MemoryRetriever and LLMClient to avoid ML/API deps.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aurora_soar.phases.collect import AgentOutput, CollectResult
from aurora_soar.phases.retrieve import RETRIEVAL_BUDGETS, retrieve_context
from aurora_soar.phases.synthesize import SynthesisResult, synthesize_results

# ---------------------------------------------------------------------------
# Retrieve phase tests
# ---------------------------------------------------------------------------


def _make_mock_retriever(code_results=None, kb_results=None, has_memory=True):
    """Create a mock MemoryRetriever with configurable results."""
    mock = MagicMock()
    mock.has_indexed_memory.return_value = has_memory
    code_results = code_results or []
    kb_results = kb_results or []

    def retrieve_side_effect(query, limit=5, min_semantic_score=0.5, chunk_type=None):
        if chunk_type == "code":
            return code_results[:limit]
        elif chunk_type == "kb":
            return kb_results[:limit]
        return (code_results + kb_results)[:limit]

    mock.retrieve.side_effect = retrieve_side_effect
    return mock


def _make_mock_chunk(chunk_id, score=0.8, chunk_type="code"):
    """Create a mock chunk with a hybrid_score."""
    chunk = MagicMock()
    chunk.id = chunk_id
    chunk.chunk_id = chunk_id
    chunk.hybrid_score = score
    chunk.type = chunk_type
    return chunk


class TestRetrieveContext:
    """Tests for retrieve_context()."""

    @pytest.mark.parametrize(
        "complexity,expected_budget",
        [
            ("SIMPLE", 5),
            ("MEDIUM", 10),
            ("COMPLEX", 15),
            ("CRITICAL", 20),
        ],
    )
    def test_budget_allocation(self, complexity, expected_budget):
        mock_store = MagicMock()
        mock_retriever = _make_mock_retriever()

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test query", complexity, mock_store)

        assert result["budget"] == expected_budget

    def test_unknown_complexity_defaults_to_medium(self):
        mock_store = MagicMock()
        mock_retriever = _make_mock_retriever()

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test", "UNKNOWN", mock_store)

        assert result["budget"] == 10  # MEDIUM default

    def test_returns_code_and_kb_chunks(self):
        mock_store = MagicMock()
        code = [_make_mock_chunk("c1"), _make_mock_chunk("c2")]
        kb = [_make_mock_chunk("kb1", chunk_type="kb")]
        mock_retriever = _make_mock_retriever(code_results=code, kb_results=kb)

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test", "MEDIUM", mock_store)

        assert result["total_retrieved"] == 3
        assert len(result["code_chunks"]) == 3  # code + kb combined

    def test_no_memory_index_returns_empty(self):
        mock_store = MagicMock()
        mock_retriever = _make_mock_retriever(has_memory=False)

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test", "SIMPLE", mock_store)

        assert result["total_retrieved"] == 0
        assert result["code_chunks"] == []
        assert result["budget_used"] == 0

    def test_high_quality_count(self):
        mock_store = MagicMock()
        code = [
            _make_mock_chunk("c1", score=0.9),  # high quality
            _make_mock_chunk("c2", score=0.7),  # high quality
            _make_mock_chunk("c3", score=0.4),  # low quality
        ]
        mock_retriever = _make_mock_retriever(code_results=code)

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test", "MEDIUM", mock_store)

        assert result["high_quality_count"] == 2

    def test_includes_retrieval_time(self):
        mock_store = MagicMock()
        mock_retriever = _make_mock_retriever()

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test", "SIMPLE", mock_store)

        assert "retrieval_time_ms" in result
        assert result["retrieval_time_ms"] >= 0

    def test_error_returns_empty_with_error_key(self):
        mock_store = MagicMock()

        with patch(
            "aurora_cli.memory.retrieval.MemoryRetriever",
            side_effect=RuntimeError("connection failed"),
        ):
            result = retrieve_context("test", "MEDIUM", mock_store)

        assert result["total_retrieved"] == 0
        assert "error" in result
        assert "connection failed" in result["error"]

    def test_respects_budget_limit(self):
        mock_store = MagicMock()
        # Return many chunks but budget should limit
        many_chunks = [_make_mock_chunk(f"c{i}") for i in range(20)]
        mock_retriever = _make_mock_retriever(code_results=many_chunks)

        with patch("aurora_cli.memory.retrieval.MemoryRetriever", return_value=mock_retriever):
            result = retrieve_context("test", "SIMPLE", mock_store)

        # SIMPLE budget=5: code_slots=3, kb_slots=2
        assert result["budget_used"] <= result["budget"]


# ---------------------------------------------------------------------------
# Synthesize phase tests
# ---------------------------------------------------------------------------


def _make_collect_result(outputs=None):
    """Create a CollectResult with given AgentOutputs."""
    if outputs is None:
        outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="agent1",
                success=True,
                summary="Completed task A",
                confidence=0.9,
            ),
        ]
    return CollectResult(
        agent_outputs=outputs,
        execution_metadata={"total_time_ms": 1000},
    )


def _make_mock_llm(answer="Test answer", confidence=0.85):
    """Create a mock LLMClient that returns a proper synthesis response."""
    mock = MagicMock()

    # reasoning.synthesize_results calls:
    # 1. llm_client.generate() for synthesis (returns response with .content)
    # 2. llm_client.generate_json() for verification (returns dict directly)
    synthesis_response = MagicMock()
    synthesis_response.content = f"ANSWER:\n{answer}\n\nCONFIDENCE: {confidence}"
    mock.generate.return_value = synthesis_response

    mock.generate_json.return_value = {
        "overall_score": confidence,
        "coherence": confidence,
        "completeness": confidence,
        "factuality": confidence,
        "issues": [],
    }

    return mock


class TestSynthesizeResults:
    """Tests for synthesize_results()."""

    def test_single_successful_output(self):
        mock_llm = _make_mock_llm()
        collect = _make_collect_result()
        decomposition = {"goal": "Test goal", "subgoals": [{"description": "Do A"}]}

        result = synthesize_results(mock_llm, "test query", collect, decomposition)

        assert isinstance(result, SynthesisResult)
        assert result.answer != ""
        assert result.confidence > 0
        assert result.metadata["subgoals_completed"] == 1
        assert result.metadata["subgoals_failed"] == 0

    def test_multiple_outputs_metadata(self):
        outputs = [
            AgentOutput(0, "a1", True, "Done A", confidence=0.9),
            AgentOutput(1, "a2", True, "Done B", confidence=0.8),
            AgentOutput(2, "a3", False, "Failed C", confidence=0.0, error="timeout"),
        ]
        collect = _make_collect_result(outputs)
        mock_llm = _make_mock_llm()
        decomposition = {
            "goal": "Test",
            "subgoals": [
                {"description": "A"},
                {"description": "B"},
                {"description": "C"},
            ],
        }

        result = synthesize_results(mock_llm, "test", collect, decomposition)

        assert result.metadata["subgoals_completed"] == 2
        assert result.metadata["subgoals_failed"] == 1

    def test_files_modified_counted(self):
        outputs = [
            AgentOutput(
                0,
                "a1",
                True,
                "Modified files",
                confidence=0.9,
                data={"files_modified": ["a.py", "b.py"]},
            ),
            AgentOutput(
                1,
                "a2",
                True,
                "More files",
                confidence=0.8,
                data={"files_modified": ["c.py"]},
            ),
        ]
        collect = _make_collect_result(outputs)
        mock_llm = _make_mock_llm()
        decomposition = {"goal": "Test", "subgoals": [{"description": "A"}, {"description": "B"}]}

        result = synthesize_results(mock_llm, "test", collect, decomposition)

        assert result.metadata["total_files_modified"] == 3

    def test_timing_info_present(self):
        mock_llm = _make_mock_llm()
        collect = _make_collect_result()
        decomposition = {"goal": "Test", "subgoals": [{"description": "A"}]}

        result = synthesize_results(mock_llm, "test", collect, decomposition)

        assert "duration_ms" in result.timing
        assert "started_at" in result.timing
        assert "completed_at" in result.timing
        assert result.timing["duration_ms"] >= 0

    def test_llm_failure_raises(self):
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = RuntimeError("API error")

        collect = _make_collect_result()
        decomposition = {"goal": "Test", "subgoals": [{"description": "A"}]}

        with pytest.raises(RuntimeError, match="Failed to synthesize"):
            synthesize_results(mock_llm, "test", collect, decomposition)


# ---------------------------------------------------------------------------
# SynthesisResult serialization tests
# ---------------------------------------------------------------------------


class TestSynthesisResult:
    """Tests for SynthesisResult data class."""

    def test_to_dict(self):
        result = SynthesisResult(
            answer="The answer",
            confidence=0.85,
            traceability=[{"claim": "X", "source": "agent1"}],
            metadata={"retry_count": 0},
            timing={"duration_ms": 100},
        )

        d = result.to_dict()
        assert d["answer"] == "The answer"
        assert d["confidence"] == 0.85
        assert len(d["traceability"]) == 1
        assert d["metadata"]["retry_count"] == 0

    def test_from_dict(self):
        data = {
            "answer": "Restored answer",
            "confidence": 0.75,
            "traceability": [],
            "metadata": {"retry_count": 1},
            "timing": {"duration_ms": 200},
        }

        result = SynthesisResult.from_dict(data)
        assert result.answer == "Restored answer"
        assert result.confidence == 0.75
        assert result.timing["duration_ms"] == 200

    def test_roundtrip(self):
        original = SynthesisResult(
            answer="Round trip test",
            confidence=0.92,
            traceability=[{"claim": "Y", "source": "agent2"}],
            metadata={"key": "value"},
            timing={"duration_ms": 50},
        )

        restored = SynthesisResult.from_dict(original.to_dict())
        assert restored.answer == original.answer
        assert restored.confidence == original.confidence
        assert restored.traceability == original.traceability
