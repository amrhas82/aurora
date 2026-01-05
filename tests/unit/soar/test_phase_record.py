"""
Unit tests for SOAR Phase 8: ACT-R Pattern Caching (Record).

Tests the record_pattern function that caches successful reasoning patterns
to ACT-R memory.
"""

from unittest.mock import MagicMock

import pytest
from aurora_core.chunks import ReasoningChunk
from aurora_core.store.base import Store
from aurora_soar.phases.collect import AgentOutput, CollectResult
from aurora_soar.phases.record import RecordResult, record_pattern
from aurora_soar.phases.synthesize import SynthesisResult


class TestRecordPatternHighScore:
    """Test suite for record_pattern with high success scores (≥0.8)."""

    def test_high_score_pattern_is_cached(self):
        """Test that patterns with score ≥0.8 are cached and marked."""
        # Setup
        store = MagicMock(spec=Store)
        query = "Implement feature X with Y and Z"
        complexity = "COMPLEX"
        decomposition = {
            "goal": "Implement feature X",
            "subgoals": [
                {"id": "sg1", "description": "Step 1"},
                {"id": "sg2", "description": "Step 2"},
            ],
            "execution_order": [{"sequential": ["sg1", "sg2"]}],
        }

        # Agent outputs with tools metadata
        agent_outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="parser-agent",
                success=True,
                summary="Parsed files successfully",
                confidence=0.9,
                execution_metadata={
                    "tools_used": ["parser", "analyzer"],
                    "tool_sequence": [{"tool": "parser", "file": "test.py"}],
                },
            ),
            AgentOutput(
                subgoal_index=1,
                agent_id="editor-agent",
                success=True,
                summary="Modified files successfully",
                confidence=0.85,
                execution_metadata={
                    "tools_used": ["editor"],
                    "tool_sequence": [{"tool": "editor", "file": "test.py"}],
                },
            ),
        ]

        collect_result = CollectResult(
            agent_outputs=agent_outputs, execution_metadata={"total_duration_ms": 1500}
        )

        synthesis_result = SynthesisResult(
            answer="Feature X implemented successfully",
            confidence=0.85,  # High score
            traceability=[],
            metadata={
                "subgoals_completed": 2,
                "subgoals_partial": 0,
                "subgoals_failed": 0,
                "total_files_modified": 3,
            },
            timing={"duration_ms": 500},
        )

        # Execute
        result = record_pattern(
            store=store,
            query=query,
            complexity=complexity,
            decomposition=decomposition,
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Verify
        assert result.cached is True
        assert result.reasoning_chunk_id is not None
        assert result.pattern_marked is True
        assert result.activation_update == 0.2  # High activation boost
        assert "duration_ms" in result.timing

        # Verify store.save_chunk was called
        store.save_chunk.assert_called_once()
        saved_chunk = store.save_chunk.call_args[0][0]
        assert isinstance(saved_chunk, ReasoningChunk)
        assert saved_chunk.pattern == query
        assert saved_chunk.complexity == complexity
        assert saved_chunk.success_score == 0.85

        # Verify store.update_activation was called
        store.update_activation.assert_called_once_with(result.reasoning_chunk_id, 0.2)

    def test_high_score_extracts_tools_correctly(self):
        """Test that tools are extracted correctly from agent outputs."""
        store = MagicMock(spec=Store)

        agent_outputs = [
            AgentOutput(
                subgoal_index=0,
                agent_id="agent1",
                success=True,
                execution_metadata={
                    "tools_used": ["tool1", "tool2"],
                    "tool_sequence": [
                        {"tool": "tool1", "action": "parse"},
                        {"tool": "tool2", "action": "analyze"},
                    ],
                },
            ),
            AgentOutput(
                subgoal_index=1,
                agent_id="agent2",
                success=True,
                execution_metadata={
                    "tools_used": ["tool2", "tool3"],  # tool2 is duplicate
                    "tool_sequence": [
                        {"tool": "tool2", "action": "edit"},
                        {"tool": "tool3", "action": "save"},
                    ],
                },
            ),
        ]

        collect_result = CollectResult(agent_outputs=agent_outputs, execution_metadata={})

        synthesis_result = SynthesisResult(
            answer="Done", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        record_pattern(
            store=store,
            query="test query",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Verify chunk has correct tools
        saved_chunk = store.save_chunk.call_args[0][0]
        assert set(saved_chunk.tools_used) == {"tool1", "tool2", "tool3"}
        assert len(saved_chunk.tool_sequence) == 4  # All 4 tool invocations

    def test_high_score_sets_metadata_correctly(self):
        """Test that ReasoningChunk metadata is set correctly."""
        store = MagicMock(spec=Store)

        decomposition = {
            "goal": "Test goal",
            "subgoals": [{"id": "sg1"}],
            "execution_order": [{"sequential": ["sg1"]}],
        }

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Test answer",
            confidence=0.92,
            traceability=[],
            metadata={
                "subgoals_completed": 5,
                "subgoals_partial": 2,
                "subgoals_failed": 1,
                "total_files_modified": 10,
            },
            timing={},
        )

        record_pattern(
            store=store,
            query="test",
            complexity="MEDIUM",
            decomposition=decomposition,
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Verify metadata
        saved_chunk = store.save_chunk.call_args[0][0]
        assert saved_chunk.metadata["decomposition_goal"] == "Test goal"
        assert saved_chunk.metadata["synthesis_confidence"] == 0.92
        assert saved_chunk.metadata["subgoals_completed"] == 5
        assert saved_chunk.metadata["subgoals_partial"] == 2
        assert saved_chunk.metadata["subgoals_failed"] == 1
        assert saved_chunk.metadata["total_files_modified"] == 10


class TestRecordPatternMediumScore:
    """Test suite for record_pattern with medium success scores (0.5-0.79)."""

    def test_medium_score_pattern_cached_but_not_marked(self):
        """Test that patterns with score 0.5-0.79 are cached but not marked as patterns."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Partial success",
            confidence=0.65,  # Medium score
            traceability=[],
            metadata={},
            timing={},
        )

        result = record_pattern(
            store=store,
            query="test query",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Verify
        assert result.cached is True
        assert result.reasoning_chunk_id is not None
        assert result.pattern_marked is False  # Not marked as pattern
        assert result.activation_update == 0.05  # Small boost

        # Verify store interactions
        store.save_chunk.assert_called_once()
        store.update_activation.assert_called_once_with(result.reasoning_chunk_id, 0.05)

    def test_medium_score_at_boundary_0_5(self):
        """Test that score exactly 0.5 is cached."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Marginal success",
            confidence=0.5,  # Exactly at threshold
            traceability=[],
            metadata={},
            timing={},
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is True
        assert result.pattern_marked is False
        assert result.activation_update == 0.05

    def test_medium_score_at_boundary_0_79(self):
        """Test that score 0.79 is cached but not marked."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Good but not great",
            confidence=0.79,  # Just below 0.8
            traceability=[],
            metadata={},
            timing={},
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is True
        assert result.pattern_marked is False
        assert result.activation_update == 0.05


class TestRecordPatternLowScore:
    """Test suite for record_pattern with low success scores (<0.5)."""

    def test_low_score_pattern_not_cached(self):
        """Test that patterns with score <0.5 are not cached."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", False, error="Failed", execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Failed attempt",
            confidence=0.3,  # Low score
            traceability=[],
            metadata={},
            timing={},
        )

        result = record_pattern(
            store=store,
            query="test query",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Verify
        assert result.cached is False
        assert result.reasoning_chunk_id is None
        assert result.pattern_marked is False
        assert result.activation_update == -0.1  # Negative penalty
        assert "duration_ms" in result.timing

        # Verify store was NOT called
        store.save_chunk.assert_not_called()
        store.update_activation.assert_not_called()

    def test_low_score_at_boundary(self):
        """Test that score just below 0.5 is not cached."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Barely failed",
            confidence=0.49,  # Just below threshold
            traceability=[],
            metadata={},
            timing={},
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is False
        store.save_chunk.assert_not_called()

    def test_zero_score_not_cached(self):
        """Test that score 0.0 is not cached."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(agent_outputs=[], execution_metadata={})

        synthesis_result = SynthesisResult(
            answer="Complete failure", confidence=0.0, traceability=[], metadata={}, timing={}
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is False
        assert result.activation_update == -0.1


class TestRecordPatternEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_missing_tools_metadata_handled_gracefully(self):
        """Test that missing tools metadata doesn't cause errors."""
        store = MagicMock(spec=Store)

        # Agent output without tools metadata
        collect_result = CollectResult(
            agent_outputs=[
                AgentOutput(
                    0,
                    "agent1",
                    True,
                    execution_metadata={},  # No tools_used or tool_sequence
                )
            ],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Should still work
        assert result.cached is True
        saved_chunk = store.save_chunk.call_args[0][0]
        assert saved_chunk.tools_used == []
        assert saved_chunk.tool_sequence == []

    def test_none_execution_metadata_handled(self):
        """Test that None execution_metadata is handled."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[
                AgentOutput(
                    0,
                    "agent1",
                    True,
                    execution_metadata=None,  # Explicitly None
                )
            ],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.85, traceability=[], metadata={}, timing={}
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is True

    def test_missing_decomposition_fields_use_defaults(self):
        """Test that missing decomposition fields use empty defaults."""
        store = MagicMock(spec=Store)

        # Decomposition without subgoals, execution_order, or goal
        decomposition = {}

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition=decomposition,
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        saved_chunk = store.save_chunk.call_args[0][0]
        assert saved_chunk.subgoals == []
        assert saved_chunk.execution_order == []
        assert saved_chunk.metadata["decomposition_goal"] == ""

    def test_missing_synthesis_metadata_fields_use_defaults(self):
        """Test that missing synthesis metadata fields use 0 defaults."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        # Synthesis with empty metadata
        synthesis_result = SynthesisResult(
            answer="Success",
            confidence=0.85,
            traceability=[],
            metadata={},  # No subgoal counts or file counts
            timing={},
        )

        record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        saved_chunk = store.save_chunk.call_args[0][0]
        assert saved_chunk.metadata["subgoals_completed"] == 0
        assert saved_chunk.metadata["subgoals_partial"] == 0
        assert saved_chunk.metadata["subgoals_failed"] == 0
        assert saved_chunk.metadata["total_files_modified"] == 0

    def test_store_save_failure_raises_runtime_error(self):
        """Test that store.save_chunk failure raises RuntimeError."""
        store = MagicMock(spec=Store)
        store.save_chunk.side_effect = Exception("Database error")

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        with pytest.raises(RuntimeError, match="Failed to cache reasoning pattern"):
            record_pattern(
                store=store,
                query="test",
                complexity="SIMPLE",
                decomposition={},
                collect_result=collect_result,
                synthesis_result=synthesis_result,
            )

    def test_store_update_activation_failure_logs_warning(self):
        """Test that store.update_activation failure logs warning but doesn't fail."""
        store = MagicMock(spec=Store)
        store.update_activation.side_effect = Exception("Activation update failed")

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        # Should not raise, just log warning
        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is True  # Still marked as cached


class TestRecordPatternChunkIdGeneration:
    """Test suite for chunk ID generation."""

    def test_chunk_id_format(self):
        """Test that chunk ID follows expected format."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        # Verify format: reasoning_<16 hex chars>
        assert result.reasoning_chunk_id.startswith("reasoning_")
        hex_part = result.reasoning_chunk_id.split("_")[1]
        assert len(hex_part) == 16
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_chunk_ids_are_unique(self):
        """Test that multiple calls generate unique chunk IDs."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        # Generate multiple IDs
        ids = set()
        for _ in range(10):
            result = record_pattern(
                store=store,
                query="test",
                complexity="SIMPLE",
                decomposition={},
                collect_result=collect_result,
                synthesis_result=synthesis_result,
            )
            ids.add(result.reasoning_chunk_id)

        # All IDs should be unique
        assert len(ids) == 10


class TestRecordResultTiming:
    """Test suite for timing information in RecordResult."""

    def test_timing_includes_required_fields(self):
        """Test that timing dict includes all required fields."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert "duration_ms" in result.timing
        assert "started_at" in result.timing
        assert "completed_at" in result.timing
        assert isinstance(result.timing["duration_ms"], int)
        assert result.timing["duration_ms"] >= 0

    def test_timing_for_skipped_cache(self):
        """Test that timing is recorded even when caching is skipped."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(agent_outputs=[], execution_metadata={})

        synthesis_result = SynthesisResult(
            answer="Failed",
            confidence=0.2,  # Low score, won't cache
            traceability=[],
            metadata={},
            timing={},
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity="SIMPLE",
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert "duration_ms" in result.timing
        assert "started_at" in result.timing
        assert "completed_at" in result.timing


class TestRecordResultToDictConversion:
    """Test suite for RecordResult.to_dict() conversion."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all RecordResult fields."""
        result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_abc123",
            pattern_marked=True,
            activation_update=0.2,
            timing={"duration_ms": 100},
        )

        result_dict = result.to_dict()

        assert result_dict["cached"] is True
        assert result_dict["reasoning_chunk_id"] == "reasoning_abc123"
        assert result_dict["pattern_marked"] is True
        assert result_dict["activation_update"] == 0.2
        assert result_dict["timing"] == {"duration_ms": 100}

    def test_to_dict_handles_none_chunk_id(self):
        """Test that to_dict handles None chunk_id (for uncached patterns)."""
        result = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=-0.1,
            timing={"duration_ms": 50},
        )

        result_dict = result.to_dict()

        assert result_dict["cached"] is False
        assert result_dict["reasoning_chunk_id"] is None
        assert result_dict["pattern_marked"] is False
        assert result_dict["activation_update"] == -0.1


class TestRecordPatternComplexityLevels:
    """Test suite for all complexity levels."""

    @pytest.mark.parametrize("complexity", ["SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"])
    def test_all_complexity_levels(self, complexity):
        """Test that all complexity levels are handled correctly."""
        store = MagicMock(spec=Store)

        collect_result = CollectResult(
            agent_outputs=[AgentOutput(0, "agent1", True, execution_metadata={})],
            execution_metadata={},
        )

        synthesis_result = SynthesisResult(
            answer="Success", confidence=0.9, traceability=[], metadata={}, timing={}
        )

        result = record_pattern(
            store=store,
            query="test",
            complexity=complexity,
            decomposition={},
            collect_result=collect_result,
            synthesis_result=synthesis_result,
        )

        assert result.cached is True
        saved_chunk = store.save_chunk.call_args[0][0]
        assert saved_chunk.complexity == complexity
