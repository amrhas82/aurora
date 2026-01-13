"""Edge case unit tests for retrieval quality handling.

Tests boundary conditions, error handling, and unusual scenarios:
- Exact threshold boundaries (activation == 0.3, groundedness == 0.7)
- Mixed quality scenarios (many low + few high chunks)
- Error handling (retrieval failures, None/negative activations)
- Empty context with reasoning chunks
- Special edge cases
"""

from unittest.mock import MagicMock, Mock

import pytest

from aurora_core.chunks.code_chunk import CodeChunk
from aurora_reasoning.verify import VerificationOption, VerificationResult, VerificationVerdict
from aurora_soar.phases.retrieve import ACTIVATION_THRESHOLD, filter_by_activation
from aurora_soar.phases.verify import RetrievalQuality, assess_retrieval_quality


class TestRetrievalQualityEdgeCases:
    """Edge case tests for retrieval quality assessment."""

    def test_exactly_3_high_quality_chunks_is_good(self):
        """Test that exactly 3 high-quality chunks with good groundedness = GOOD quality."""
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.7,  # Exactly at threshold
            routability=0.8,
            overall_score=0.775,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification,
            high_quality_chunks=3,  # Exactly at threshold
            total_chunks=5,
        )

        assert quality == RetrievalQuality.GOOD

    def test_exactly_0_7_groundedness_is_good(self):
        """Test that exactly 0.7 groundedness is considered good (boundary inclusive)."""
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.7,  # Exactly at threshold
            routability=0.8,
            overall_score=0.775,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=5, total_chunks=5
        )

        assert quality == RetrievalQuality.GOOD

    def test_weak_chunks_with_high_total_count(self):
        """Test that many chunks with all low activation = WEAK quality."""
        verification = VerificationResult(
            completeness=0.7,
            consistency=0.7,
            groundedness=0.65,  # Low
            routability=0.7,
            overall_score=0.6875,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # 10 total chunks but 0 high-quality
        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=0, total_chunks=10
        )

        assert quality == RetrievalQuality.WEAK

    def test_mixed_quality_chunks(self):
        """Test filtering with mix of high and low quality chunks."""
        # Create chunks with various activation levels
        chunks = []
        for i in range(5):
            chunk = Mock(spec=CodeChunk)
            chunk.id = f"chunk{i}"
            chunks.append(chunk)

        # Mock store that returns different activations
        mock_store = Mock()

        def get_activation_side_effect(chunk_id):
            if chunk_id in ["chunk0", "chunk1"]:
                return 0.5  # High quality (>= 0.3)
            else:
                return 0.1  # Low quality (< 0.3)

        mock_store.get_activation = Mock(side_effect=get_activation_side_effect)

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        # Should count only chunk0 and chunk1 as high-quality
        assert high_quality_count == 2

    def test_retrieval_error_treated_as_no_match(self):
        """Test that total_chunks=0 (error scenario) returns NONE quality."""
        verification = VerificationResult(
            completeness=0.5,
            consistency=0.5,
            groundedness=0.0,  # Doesn't matter
            routability=0.5,
            overall_score=0.375,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification,
            high_quality_chunks=0,
            total_chunks=0,  # Error/no retrieval
        )

        assert quality == RetrievalQuality.NONE

    def test_activation_threshold_exactly_0_3(self):
        """Test that activation exactly at 0.3 counts as high-quality."""
        chunks = [Mock(spec=CodeChunk, id="chunk0")]

        mock_store = Mock()
        mock_store.get_activation = Mock(return_value=ACTIVATION_THRESHOLD)  # Exactly 0.3

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        # activation >= 0.3, so should count as high-quality
        assert high_quality_count == 1

    def test_activation_just_below_threshold(self):
        """Test that activation just below 0.3 doesn't count as high-quality."""
        chunks = [Mock(spec=CodeChunk, id="chunk0")]

        mock_store = Mock()
        mock_store.get_activation = Mock(return_value=0.2999)  # Just below 0.3

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        assert high_quality_count == 0

    def test_negative_activation_filtered(self):
        """Test that negative activation is handled gracefully."""
        chunks = [Mock(spec=CodeChunk, id="chunk0")]

        mock_store = Mock()
        mock_store.get_activation = Mock(return_value=-0.5)  # Negative (shouldn't happen)

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        # Negative activation should not count as high-quality
        assert high_quality_count == 0

    def test_none_activation_filtered(self):
        """Test that None activation is handled gracefully."""
        chunks = [Mock(spec=CodeChunk, id="chunk0")]

        mock_store = Mock()
        mock_store.get_activation = Mock(return_value=None)  # Database error scenario

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        # None should be treated as low-quality
        assert high_quality_count == 0

    def test_store_exception_handled_gracefully(self):
        """Test that exceptions from store.get_activation() are handled."""
        chunks = [Mock(spec=CodeChunk, id="chunk0"), Mock(spec=CodeChunk, id="chunk1")]

        mock_store = Mock()
        # First call raises exception, second call succeeds
        mock_store.get_activation = Mock(side_effect=[Exception("DB error"), 0.5])

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        # Should handle exception and continue, counting only the second chunk
        assert high_quality_count == 1

    def test_groundedness_just_below_threshold(self):
        """Test that groundedness just below 0.7 results in WEAK quality."""
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.6999,  # Just below 0.7
            routability=0.8,
            overall_score=0.7749,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification,
            high_quality_chunks=5,  # Enough chunks
            total_chunks=5,
        )

        assert quality == RetrievalQuality.WEAK

    def test_2_high_quality_chunks_is_weak(self):
        """Test that exactly 2 high-quality chunks (just below threshold) = WEAK."""
        verification = VerificationResult(
            completeness=0.8,
            consistency=0.8,
            groundedness=0.8,  # Good groundedness
            routability=0.8,
            overall_score=0.8,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification,
            high_quality_chunks=2,  # Just below threshold of 3
            total_chunks=10,
        )

        assert quality == RetrievalQuality.WEAK

    def test_filter_by_activation_no_store(self):
        """Test filter_by_activation falls back to chunk attributes when no store."""
        # Create chunks with activation attributes
        chunks = [
            Mock(spec=CodeChunk, id="chunk0", activation=0.5),
            Mock(spec=CodeChunk, id="chunk1", activation=0.2),
            Mock(spec=CodeChunk, id="chunk2", activation=0.4),
        ]

        _, high_quality_count = filter_by_activation(chunks, store=None)

        # Should count chunk0 (0.5) and chunk2 (0.4) as high-quality
        assert high_quality_count == 2

    def test_filter_by_activation_chunk_without_activation_attribute(self):
        """Test that chunks without activation attribute default to 0.0."""
        chunks = [Mock(spec=CodeChunk, id="chunk0")]  # No activation attribute

        _, high_quality_count = filter_by_activation(chunks, store=None)

        # Should default to 0.0 and not count as high-quality
        assert high_quality_count == 0

    def test_empty_chunks_list(self):
        """Test that empty chunks list returns 0 high-quality count."""
        chunks = []
        mock_store = Mock()

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        assert high_quality_count == 0

    def test_very_high_activation(self):
        """Test that very high activation (> 1.0) counts as high-quality."""
        chunks = [Mock(spec=CodeChunk, id="chunk0")]

        mock_store = Mock()
        mock_store.get_activation = Mock(return_value=5.0)  # Very high

        _, high_quality_count = filter_by_activation(chunks, store=mock_store)

        assert high_quality_count == 1

    def test_zero_groundedness(self):
        """Test that 0.0 groundedness results in WEAK quality."""
        verification = VerificationResult(
            completeness=0.5,
            consistency=0.5,
            groundedness=0.0,  # Zero
            routability=0.5,
            overall_score=0.375,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=5, total_chunks=5
        )

        assert quality == RetrievalQuality.WEAK

    def test_perfect_groundedness(self):
        """Test that 1.0 groundedness with sufficient chunks = GOOD quality."""
        verification = VerificationResult(
            completeness=1.0,
            consistency=1.0,
            groundedness=1.0,  # Perfect
            routability=1.0,
            overall_score=1.0,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        quality = assess_retrieval_quality(
            verification=verification, high_quality_chunks=3, total_chunks=3
        )

        assert quality == RetrievalQuality.GOOD
