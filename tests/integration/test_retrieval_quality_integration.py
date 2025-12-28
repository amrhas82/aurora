"""Integration tests for retrieval quality handling.

Tests the SOAR phases working together to assess and handle retrieval quality:
1. No matches (0 chunks)
2. Weak matches (low groundedness or < 3 high-quality chunks)
3. Good matches (high groundedness and >= 3 high-quality chunks)
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from aurora_reasoning.verify import VerificationOption, VerificationResult, VerificationVerdict

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_core.store.sqlite import SQLiteStore
from aurora_soar.phases.retrieve import ACTIVATION_THRESHOLD, retrieve_context
from aurora_soar.phases.verify import RetrievalQuality, assess_retrieval_quality


class TestRetrievalQualityIntegration:
    """Integration tests for retrieval quality assessment across SOAR phases."""

    @pytest.fixture
    def temp_store(self):
        """Create temporary SQLite store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteStore(str(db_path))
            yield store
            store.close()

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.integration
    def test_no_match_scenario_quality_assessment(self, temp_store):
        """Test NONE quality when retrieval returns 0 chunks."""
        # Empty store - no chunks
        retrieval_result = retrieve_context(
            query="nonexistent code", store=temp_store, complexity="MEDIUM"
        )

        assert retrieval_result["total_retrieved"] == 0
        assert retrieval_result["high_quality_count"] == 0

        # Create mock verification result
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.5,  # Doesn't matter for NONE
            routability=0.8,
            overall_score=0.75,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Assess quality
        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=0, total_chunks=0
        )

        assert quality == RetrievalQuality.NONE

    @pytest.mark.integration
    def test_weak_match_low_groundedness(self, temp_store):
        """Test WEAK quality when groundedness < 0.7 even with enough chunks."""
        # Add 5 high-quality chunks (activation >= 0.3)
        for i in range(5):
            chunk = CodeChunk(
                chunk_id=f"chunk{i}",
                file_path=f"/test/file{i}.py",
                element_type="function",
                name=f"func{i}",
                line_start=1,
                line_end=1,
                signature=f"def func{i}(): pass",
                language="python",
            )
            temp_store.save_chunk(chunk)
            # Record access first to create activation entry, then update
            temp_store.record_access(chunk.id, datetime.now(timezone.utc))
            temp_store.update_activation(chunk.id, 0.5)  # High activation

        # Retrieve
        retrieval_result = retrieve_context(
            query="test query", store=temp_store, complexity="MEDIUM"
        )

        assert retrieval_result["high_quality_count"] == 5  # All high-quality
        assert retrieval_result["total_retrieved"] == 5

        # Create verification with LOW groundedness
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.6,  # < 0.7 → WEAK
            routability=0.8,
            overall_score=0.75,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Assess quality
        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=5, total_chunks=5
        )

        assert quality == RetrievalQuality.WEAK

    @pytest.mark.integration
    def test_weak_match_insufficient_high_quality_chunks(self, temp_store):
        """Test WEAK quality when < 3 high-quality chunks even with good groundedness."""
        # Add 2 high-quality chunks (not enough)
        for i in range(2):
            chunk = CodeChunk(
                chunk_id=f"good{i}",
                file_path=f"/test/file{i}.py",
                element_type="function",
                name=f"good_func{i}",
                line_start=1,
                line_end=1,
                signature=f"def good_func{i}(): pass",
                language="python",
            )
            temp_store.save_chunk(chunk)
            # Record access first to create activation entry
            temp_store.record_access(chunk.id, datetime.now(timezone.utc))
            temp_store.update_activation(chunk.id, 0.5)  # High activation

        # Retrieve
        retrieval_result = retrieve_context(
            query="test query", store=temp_store, complexity="MEDIUM"
        )

        assert retrieval_result["high_quality_count"] == 2  # < 3
        assert retrieval_result["total_retrieved"] == 2

        # Create verification with HIGH groundedness
        verification = VerificationResult(
            completeness=0.9,
            consistency=0.9,
            groundedness=0.8,  # >= 0.7 (good)
            routability=0.9,
            overall_score=0.875,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Assess quality - should still be WEAK due to < 3 chunks
        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=2, total_chunks=2
        )

        assert quality == RetrievalQuality.WEAK

    @pytest.mark.integration
    def test_weak_match_many_low_quality_chunks(self, temp_store):
        """Test WEAK quality when many chunks but all have low activation."""
        # Add 10 chunks but all with activation < 0.3
        for i in range(10):
            chunk = CodeChunk(
                chunk_id=f"weak{i}",
                file_path=f"/test/file{i}.py",
                element_type="function",
                name=f"weak_func{i}",
                line_start=1,
                line_end=1,
                signature=f"def weak_func{i}(): pass",
                language="python",
            )
            temp_store.save_chunk(chunk)
            # Record access first to create activation entry
            temp_store.record_access(chunk.id, datetime.now(timezone.utc))
            temp_store.update_activation(chunk.id, 0.2)  # < ACTIVATION_THRESHOLD

        # Retrieve
        retrieval_result = retrieve_context(
            query="test query", store=temp_store, complexity="MEDIUM"
        )

        assert retrieval_result["total_retrieved"] == 10  # Many chunks
        assert retrieval_result["high_quality_count"] == 0  # But none high-quality

        # Create verification
        verification = VerificationResult(
            completeness=0.7,
            consistency=0.7,
            groundedness=0.65,  # < 0.7
            routability=0.7,
            overall_score=0.69,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Assess quality - WEAK due to 0 high-quality chunks
        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=0, total_chunks=10
        )

        assert quality == RetrievalQuality.WEAK

    @pytest.mark.integration
    def test_good_match_sufficient_quality(self, temp_store):
        """Test GOOD quality when groundedness >= 0.7 AND >= 3 high-quality chunks."""
        # Add 5 high-quality chunks
        for i in range(5):
            chunk = CodeChunk(
                chunk_id=f"good{i}",
                file_path=f"/test/file{i}.py",
                element_type="function",
                name=f"good_func{i}",
                line_start=1,
                line_end=1,
                signature=f"def good_func{i}(): pass",
                language="python",
            )
            temp_store.save_chunk(chunk)
            # Record access first to create activation entry
            temp_store.record_access(chunk.id, datetime.now(timezone.utc))
            temp_store.update_activation(chunk.id, 0.5 + i * 0.1)  # >= 0.3

        # Retrieve
        retrieval_result = retrieve_context(
            query="good query", store=temp_store, complexity="MEDIUM"
        )

        assert retrieval_result["high_quality_count"] == 5
        assert retrieval_result["total_retrieved"] == 5

        # Create verification with high groundedness
        verification = VerificationResult(
            completeness=0.9,
            consistency=0.9,
            groundedness=0.8,  # >= 0.7
            routability=0.9,
            overall_score=0.875,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Assess quality
        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=5, total_chunks=5
        )

        assert quality == RetrievalQuality.GOOD

    @pytest.mark.integration
    def test_activation_threshold_boundary(self, temp_store):
        """Test that activation exactly at 0.3 counts as high-quality."""
        # Add chunk with activation exactly at threshold
        chunk = CodeChunk(
            chunk_id="boundary",
            file_path="/test/file.py",
            element_type="function",
            name="boundary_func",
            line_start=1,
            line_end=1,
            signature="def boundary_func(): pass",
            language="python",
        )
        temp_store.save_chunk(chunk)
        # Record access first to create activation entry
        temp_store.record_access(chunk.id, datetime.now(timezone.utc))
        temp_store.update_activation(chunk.id, ACTIVATION_THRESHOLD)  # Exactly 0.3

        # Retrieve
        retrieval_result = retrieve_context(
            query="boundary test", store=temp_store, complexity="MEDIUM"
        )

        # Activation >= 0.3 should count as high-quality
        assert retrieval_result["high_quality_count"] == 1
        assert retrieval_result["total_retrieved"] == 1

    @pytest.mark.integration
    def test_retrieval_quality_with_mixed_activations(self, temp_store):
        """Test retrieval with mix of high and low activation chunks."""
        # Add 3 high-quality and 3 low-quality chunks
        for i in range(3):
            high_chunk = CodeChunk(
                chunk_id=f"high{i}",
                file_path=f"/test/high{i}.py",
                element_type="function",
                name=f"high_func{i}",
                line_start=1,
                line_end=1,
                signature=f"def high_func{i}(): pass",
                language="python",
            )
            temp_store.save_chunk(high_chunk)
            # Record access first to create activation entry
            temp_store.record_access(high_chunk.id, datetime.now(timezone.utc))
            temp_store.update_activation(high_chunk.id, 0.6)  # High

            low_chunk = CodeChunk(
                chunk_id=f"low{i}",
                file_path=f"/test/low{i}.py",
                element_type="function",
                name=f"low_func{i}",
                line_start=1,
                line_end=1,
                signature=f"def low_func{i}(): pass",
                language="python",
            )
            temp_store.save_chunk(low_chunk)
            # Record access first to create activation entry
            temp_store.record_access(low_chunk.id, datetime.now(timezone.utc))
            temp_store.update_activation(low_chunk.id, 0.1)  # Low

        # Retrieve
        retrieval_result = retrieve_context(
            query="mixed test", store=temp_store, complexity="MEDIUM"
        )

        assert retrieval_result["total_retrieved"] == 6
        assert retrieval_result["high_quality_count"] == 3  # Only high activation ones

        # With exactly 3 high-quality chunks and high groundedness → GOOD
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.75,  # >= 0.7
            routability=0.8,
            overall_score=0.7875,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=3, total_chunks=6
        )

        assert quality == RetrievalQuality.GOOD  # Exactly at boundary
