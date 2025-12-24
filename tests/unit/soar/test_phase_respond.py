"""
Unit tests for SOAR Phase 9: Response Formatting (Respond).

Tests the format_response function that formats final responses with
different verbosity levels (QUIET, NORMAL, VERBOSE, JSON).
"""

import json

from aurora.soar.phases.record import RecordResult
from aurora.soar.phases.respond import (
    ResponseResult,
    Verbosity,
    format_response,
)
from aurora.soar.phases.synthesize import SynthesisResult


class TestFormatResponseQuiet:
    """Test suite for QUIET verbosity level."""

    def test_quiet_format_high_score(self):
        """Test QUIET format with high confidence score (≥0.7)."""
        synthesis_result = SynthesisResult(
            answer="Feature X has been successfully implemented with all tests passing.",
            confidence=0.85,
            traceability=[],
            metadata={},
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_abc123",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.QUIET,
        )

        # Verify format
        assert "✓" in result.formatted_output  # Success checkmark
        assert "0.85" in result.formatted_output
        assert "Feature X has been successfully" in result.formatted_output

    def test_quiet_format_medium_score(self):
        """Test QUIET format with medium confidence score (0.5-0.69)."""
        synthesis_result = SynthesisResult(
            answer="Partial success achieved.",
            confidence=0.6,
            traceability=[],
            metadata={},
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_xyz",
            pattern_marked=False,
            activation_update=0.05,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.QUIET,
        )

        # Verify format
        assert "⚠" in result.formatted_output  # Warning symbol
        assert "0.60" in result.formatted_output

    def test_quiet_format_low_score(self):
        """Test QUIET format with low confidence score (<0.5)."""
        synthesis_result = SynthesisResult(
            answer="Task failed to complete.",
            confidence=0.3,
            traceability=[],
            metadata={},
            timing={},
        )

        record_result = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=-0.1,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.QUIET,
        )

        # Verify format
        assert "✗" in result.formatted_output  # Failure symbol
        assert "0.30" in result.formatted_output

    def test_quiet_truncates_long_answer(self):
        """Test that QUIET format truncates answers longer than 100 chars."""
        long_answer = "A" * 200  # 200 character answer

        synthesis_result = SynthesisResult(
            answer=long_answer, confidence=0.8, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_test",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.QUIET,
        )

        # Verify truncation
        assert len(result.formatted_output) < len(long_answer)
        assert "..." in result.formatted_output


class TestFormatResponseNormal:
    """Test suite for NORMAL verbosity level."""

    def test_normal_format_complete_structure(self):
        """Test that NORMAL format includes all expected sections."""
        synthesis_result = SynthesisResult(
            answer="Task completed successfully.",
            confidence=0.85,
            traceability=[],
            metadata={
                "subgoals_completed": 3,
                "subgoals_partial": 1,
                "subgoals_failed": 0,
                "total_files_modified": 5,
            },
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_normal",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        phase_metadata = {
            "phases": {
                "assess": {"duration_ms": 50},
                "retrieve": {"duration_ms": 100},
                "decompose": {"duration_ms": 500},
            }
        }

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata=phase_metadata,
            verbosity=Verbosity.NORMAL,
        )

        output = result.formatted_output

        # Verify sections present
        assert "SOAR PIPELINE RESULT" in output
        assert "ANSWER:" in output
        assert "Task completed successfully." in output
        assert "KEY METRICS:" in output
        assert "Confidence: 0.85" in output
        assert "Subgoals: 3 completed, 1 partial, 0 failed" in output
        assert "Files Modified: 5" in output
        assert "PHASE SUMMARY:" in output
        assert "assess: 50ms" in output
        assert "retrieve: 100ms" in output
        assert "decompose: 500ms" in output
        assert "CACHING:" in output
        assert "Marked as pattern" in output
        assert "reasoning_normal" in output

    def test_normal_format_cached_for_learning(self):
        """Test NORMAL format when pattern is cached but not marked."""
        synthesis_result = SynthesisResult(
            answer="Partial success.", confidence=0.65, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_learning",
            pattern_marked=False,  # Not marked as pattern
            activation_update=0.05,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.NORMAL,
        )

        output = result.formatted_output

        assert "Cached for learning" in output
        assert "reasoning_learning" in output

    def test_normal_format_not_cached(self):
        """Test NORMAL format when pattern is not cached."""
        synthesis_result = SynthesisResult(
            answer="Low quality result.", confidence=0.3, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=-0.1,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.NORMAL,
        )

        output = result.formatted_output

        assert "Not cached (low quality)" in output

    def test_normal_format_missing_metadata_uses_defaults(self):
        """Test NORMAL format with missing metadata fields uses defaults."""
        synthesis_result = SynthesisResult(
            answer="Test answer.",
            confidence=0.8,
            traceability=[],
            metadata={},  # Empty metadata
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="test",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.NORMAL,
        )

        output = result.formatted_output

        # Verify defaults (0 for all counts)
        assert "Subgoals: 0 completed, 0 partial, 0 failed" in output
        assert "Files Modified: 0" in output


class TestFormatResponseVerbose:
    """Test suite for VERBOSE verbosity level."""

    def test_verbose_format_complete_structure(self):
        """Test that VERBOSE format includes all expected sections."""
        synthesis_result = SynthesisResult(
            answer="Comprehensive implementation complete.",
            confidence=0.92,
            traceability=[
                {
                    "agent": "parser-agent",
                    "subgoal_id": "sg1",
                    "subgoal_description": "Parse source files",
                },
                {
                    "agent": "editor-agent",
                    "subgoal_id": "sg2",
                    "subgoal_description": "Modify files",
                },
            ],
            metadata={
                "verification_score": 0.88,
                "coherence": 0.9,
                "completeness": 0.95,
                "factuality": 0.91,
                "subgoals_completed": 5,
                "subgoals_partial": 2,
                "subgoals_failed": 1,
                "total_files_modified": 10,
                "user_interactions_count": 3,
            },
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_verbose",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        phase_metadata = {
            "phases": {
                "assess": {"duration_ms": 50},
                "retrieve": {"duration_ms": 100},
                "decompose": {"duration_ms": 500},
                "verify": {"duration_ms": 800},
            },
            "cost": {
                "estimated_usd": 0.0125,
                "actual_usd": 0.0138,
                "tokens_used": {"input": 2500, "output": 1200, "total": 3700},
            },
        }

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata=phase_metadata,
            verbosity=Verbosity.VERBOSE,
        )

        output = result.formatted_output

        # Verify all sections
        assert "SOAR PIPELINE VERBOSE TRACE" in output
        assert "ANSWER" in output
        assert "Comprehensive implementation complete." in output
        assert "CONFIDENCE & QUALITY SCORES" in output
        assert "Overall Confidence: 0.92" in output
        assert "Verification Score: 0.88" in output
        assert "Coherence: 0.90" in output
        assert "Completeness: 0.95" in output
        assert "Factuality: 0.91" in output
        assert "TRACEABILITY" in output
        assert "1. Agent: parser-agent" in output
        assert "2. Agent: editor-agent" in output
        assert "EXECUTION SUMMARY" in output
        assert "Subgoals Completed: 5" in output
        assert "Subgoals Partial: 2" in output
        assert "Subgoals Failed: 1" in output
        assert "Files Modified: 10" in output
        assert "User Interactions: 3" in output
        assert "PHASE TIMING" in output
        assert "assess: 50ms" in output
        assert "Total Duration: 1450ms" in output
        assert "PATTERN CACHING" in output
        assert "Status: Pattern" in output
        assert "Activation Update: +0.20" in output
        assert "COST TRACKING" in output
        assert "Estimated Cost: $0.0125" in output
        assert "Actual Cost: $0.0138" in output
        assert "Tokens: 2500 input + 1200 output = 3700 total" in output

    def test_verbose_format_empty_traceability(self):
        """Test VERBOSE format with no traceability information."""
        synthesis_result = SynthesisResult(
            answer="Test answer.",
            confidence=0.8,
            traceability=[],  # No traceability
            metadata={},
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="test",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.VERBOSE,
        )

        output = result.formatted_output

        assert "TRACEABILITY" in output
        assert "No traceability information available" in output

    def test_verbose_format_not_cached(self):
        """Test VERBOSE format when pattern is not cached."""
        synthesis_result = SynthesisResult(
            answer="Low quality.", confidence=0.3, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=-0.1,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.VERBOSE,
        )

        output = result.formatted_output

        assert "Status: Not cached (score < 0.5)" in output
        assert "Activation Update: -0.10" in output

    def test_verbose_format_cached_not_pattern(self):
        """Test VERBOSE format when cached but not marked as pattern."""
        synthesis_result = SynthesisResult(
            answer="Medium quality.", confidence=0.65, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_cache",
            pattern_marked=False,
            activation_update=0.05,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.VERBOSE,
        )

        output = result.formatted_output

        assert "Status: Cached" in output
        assert "Chunk ID: reasoning_cache" in output
        assert "Activation Update: +0.05" in output


class TestFormatResponseJSON:
    """Test suite for JSON verbosity level."""

    def test_json_format_is_valid_json(self):
        """Test that JSON format produces valid, parseable JSON."""
        synthesis_result = SynthesisResult(
            answer="Test answer.",
            confidence=0.85,
            traceability=[{"agent": "test-agent", "subgoal_id": "sg1"}],
            metadata={"key": "value"},
            timing={"duration_ms": 100},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_json",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        phase_metadata = {"phase": "data"}

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata=phase_metadata,
            verbosity=Verbosity.JSON,
        )

        # Verify output is valid JSON
        parsed = json.loads(result.formatted_output)
        assert isinstance(parsed, dict)

    def test_json_format_includes_all_fields(self):
        """Test that JSON format includes all required fields."""
        synthesis_result = SynthesisResult(
            answer="Test answer.",
            confidence=0.88,
            traceability=[{"trace": "data"}],
            metadata={"synthesis": "metadata"},
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_complete",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        phase_metadata = {"custom": "metadata", "phase_count": 9}

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata=phase_metadata,
            verbosity=Verbosity.JSON,
        )

        parsed = json.loads(result.formatted_output)

        # Verify top-level fields
        assert parsed["answer"] == "Test answer."
        assert parsed["confidence"] == 0.88
        assert parsed["overall_score"] == 0.88
        assert "reasoning_trace" in parsed
        assert parsed["reasoning_trace"]["traceability"] == [{"trace": "data"}]
        assert parsed["reasoning_trace"]["synthesis_metadata"] == {"synthesis": "metadata"}
        assert "metadata" in parsed
        assert parsed["metadata"]["cached"] is True
        assert parsed["metadata"]["reasoning_chunk_id"] == "reasoning_complete"
        assert parsed["metadata"]["pattern_marked"] is True
        assert parsed["metadata"]["custom"] == "metadata"
        assert parsed["metadata"]["phase_count"] == 9

    def test_json_format_with_none_chunk_id(self):
        """Test JSON format when reasoning_chunk_id is None (not cached)."""
        synthesis_result = SynthesisResult(
            answer="Low quality.", confidence=0.3, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=-0.1,
            timing={},
        )

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata={},
            verbosity=Verbosity.JSON,
        )

        parsed = json.loads(result.formatted_output)

        assert parsed["metadata"]["cached"] is False
        assert parsed["metadata"]["reasoning_chunk_id"] is None
        assert parsed["metadata"]["pattern_marked"] is False


class TestResponseResultClass:
    """Test suite for ResponseResult class methods."""

    def test_response_result_initialization(self):
        """Test ResponseResult initialization."""
        raw_data = {"answer": "test", "confidence": 0.9, "metadata": {}}

        result = ResponseResult(formatted_output="formatted test", raw_data=raw_data)

        assert result.formatted_output == "formatted test"
        assert result.raw_data == raw_data

    def test_response_result_to_dict(self):
        """Test ResponseResult.to_dict() returns raw_data."""
        raw_data = {
            "answer": "test answer",
            "confidence": 0.85,
            "overall_score": 0.85,
            "metadata": {"key": "value"},
        }

        result = ResponseResult(formatted_output="formatted", raw_data=raw_data)

        result_dict = result.to_dict()

        assert result_dict == raw_data
        assert result_dict is raw_data  # Should be the same object


class TestVerbosityEnum:
    """Test suite for Verbosity enum."""

    def test_verbosity_enum_values(self):
        """Test that Verbosity enum has all expected values."""
        assert Verbosity.QUIET.value == "quiet"
        assert Verbosity.NORMAL.value == "normal"
        assert Verbosity.VERBOSE.value == "verbose"
        assert Verbosity.JSON.value == "json"

    def test_verbosity_is_string_enum(self):
        """Test that Verbosity values are strings."""
        assert isinstance(Verbosity.QUIET, str)
        assert isinstance(Verbosity.NORMAL, str)
        assert isinstance(Verbosity.VERBOSE, str)
        assert isinstance(Verbosity.JSON, str)


class TestFormatResponseDefaultVerbosity:
    """Test suite for default verbosity behavior."""

    def test_default_verbosity_is_normal(self):
        """Test that default verbosity is NORMAL."""
        synthesis_result = SynthesisResult(
            answer="Test.", confidence=0.8, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="test",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        # Call without verbosity parameter
        result = format_response(
            synthesis_result=synthesis_result, record_result=record_result, phase_metadata={}
        )

        # Should produce NORMAL format
        assert "SOAR PIPELINE RESULT" in result.formatted_output
        assert "KEY METRICS:" in result.formatted_output


class TestFormatResponseRawData:
    """Test suite for raw_data structure."""

    def test_raw_data_structure_is_consistent(self):
        """Test that raw_data has consistent structure across verbosity levels."""
        synthesis_result = SynthesisResult(
            answer="Test answer.",
            confidence=0.85,
            traceability=[
                {"agent": "test-agent", "subgoal_id": "sg1", "subgoal_description": "Test subgoal"}
            ],
            metadata={"meta": "data"},
            timing={},
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="reasoning_test",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        phase_metadata = {"phase": "metadata"}

        # Test all verbosity levels
        for verbosity in [Verbosity.QUIET, Verbosity.NORMAL, Verbosity.VERBOSE, Verbosity.JSON]:
            result = format_response(
                synthesis_result=synthesis_result,
                record_result=record_result,
                phase_metadata=phase_metadata,
                verbosity=verbosity,
            )

            # Verify raw_data structure is the same
            assert result.raw_data["answer"] == "Test answer."
            assert result.raw_data["confidence"] == 0.85
            assert result.raw_data["overall_score"] == 0.85
            assert "reasoning_trace" in result.raw_data
            assert "metadata" in result.raw_data
            assert result.raw_data["metadata"]["cached"] is True
            assert result.raw_data["metadata"]["reasoning_chunk_id"] == "reasoning_test"

    def test_raw_data_includes_phase_metadata(self):
        """Test that raw_data includes phase_metadata fields."""
        synthesis_result = SynthesisResult(
            answer="Test.", confidence=0.8, traceability=[], metadata={}, timing={}
        )

        record_result = RecordResult(
            cached=True,
            reasoning_chunk_id="test",
            pattern_marked=True,
            activation_update=0.2,
            timing={},
        )

        phase_metadata = {
            "total_duration_ms": 5000,
            "llm_calls": 10,
            "custom_field": "custom_value",
        }

        result = format_response(
            synthesis_result=synthesis_result,
            record_result=record_result,
            phase_metadata=phase_metadata,
            verbosity=Verbosity.QUIET,
        )

        # Phase metadata should be merged into result metadata
        assert result.raw_data["metadata"]["total_duration_ms"] == 5000
        assert result.raw_data["metadata"]["llm_calls"] == 10
        assert result.raw_data["metadata"]["custom_field"] == "custom_value"
