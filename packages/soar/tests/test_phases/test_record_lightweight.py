"""TDD Tests for lightweight record phase."""

import time

from aurora_soar.phases.record import SummaryRecord


def test_summary_record_creation():
    """Test SummaryRecord dataclass can be created with all fields."""
    record = SummaryRecord(
        id="test-id",
        query="test query",
        summary="test summary",
        confidence=0.85,
        log_file="/path/to/log.txt",
        keywords=["test", "query"],
        timestamp=time.time(),
    )

    assert record.id == "test-id"
    assert record.query == "test query"
    assert record.summary == "test summary"
    assert record.confidence == 0.85
    assert record.log_file == "/path/to/log.txt"
    assert record.keywords == ["test", "query"]
    assert isinstance(record.timestamp, float)


def test_summary_record_to_dict():
    """Test SummaryRecord.to_dict() returns expected structure."""
    timestamp = time.time()
    record = SummaryRecord(
        id="test-id",
        query="test query",
        summary="test summary",
        confidence=0.85,
        log_file="/path/to/log.txt",
        keywords=["test", "query"],
        timestamp=timestamp,
    )

    result = record.to_dict()

    assert isinstance(result, dict)
    assert result["id"] == "test-id"
    assert result["query"] == "test query"
    assert result["summary"] == "test summary"
    assert result["confidence"] == 0.85
    assert result["log_file"] == "/path/to/log.txt"
    assert result["keywords"] == ["test", "query"]
    assert result["timestamp"] == timestamp


# ============================================================================
# TDD Tests for record_pattern_lightweight function
# ============================================================================


class TestRecordPatternLightweight:
    """TDD tests for record_pattern_lightweight function."""

    def test_high_confidence_creates_record(self):
        """Test record created when confidence >= 0.8."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.85
        synthesis_result.summary = "Test summary"

        result = record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        assert result.cached is True
        assert result.reasoning_chunk_id is not None

    def test_medium_confidence_creates_record(self):
        """Test record created when confidence >= 0.5."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.6
        synthesis_result.summary = "Test summary"

        result = record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        assert result.cached is True
        assert result.reasoning_chunk_id is not None

    def test_low_confidence_skips_caching(self):
        """Test caching skipped when confidence < 0.5."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.3
        synthesis_result.summary = "Test summary"

        result = record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        assert result.cached is False
        assert result.reasoning_chunk_id is None

    def test_query_truncated_to_200_chars(self):
        """Test long query truncated to 200 characters."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.8
        synthesis_result.summary = "Test summary"

        long_query = "a" * 300
        record_pattern_lightweight(
            store=store,
            query=long_query,
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        # Verify store.save_chunk was called with truncated query
        assert store.save_chunk.called
        saved_chunk = store.save_chunk.call_args[0][0]
        assert len(saved_chunk.pattern) <= 200

    def test_summary_truncated_to_500_chars(self):
        """Test long summary truncated to 500 characters."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.8
        synthesis_result.summary = "b" * 600

        record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        # Verify summary was truncated
        assert store.save_chunk.called
        saved_chunk = store.save_chunk.call_args[0][0]
        # Check that summary in metadata is truncated
        assert len(saved_chunk.metadata.get("summary", "")) <= 500

    def test_log_file_path_included(self):
        """Test log_path stored correctly in record."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.8
        synthesis_result.summary = "Test summary"

        record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/custom/path/log.txt",
        )

        assert store.save_chunk.called
        saved_chunk = store.save_chunk.call_args[0][0]
        assert saved_chunk.metadata.get("log_file") == "/custom/path/log.txt"

    def test_keywords_extracted(self):
        """Test keywords list populated from query and summary."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.8
        synthesis_result.summary = "Python function test example"

        record_pattern_lightweight(
            store=store,
            query="create python function test",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        assert store.save_chunk.called
        saved_chunk = store.save_chunk.call_args[0][0]
        keywords = saved_chunk.metadata.get("keywords", [])
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_activation_boost_for_patterns(self):
        """Test confidence >= 0.8 gets activation boost of +0.2."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.85
        synthesis_result.summary = "Test summary"

        result = record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        assert result.pattern_marked is True
        assert result.activation_update == 0.2

    def test_activation_boost_for_learning(self):
        """Test confidence >= 0.5 gets activation boost of +0.05."""
        from unittest.mock import MagicMock

        from aurora_soar.phases.record import record_pattern_lightweight

        store = MagicMock()
        synthesis_result = MagicMock()
        synthesis_result.confidence = 0.6
        synthesis_result.summary = "Test summary"

        result = record_pattern_lightweight(
            store=store,
            query="test query",
            synthesis_result=synthesis_result,
            log_path="/path/to/log.txt",
        )

        assert result.pattern_marked is False
        assert result.activation_update == 0.05
